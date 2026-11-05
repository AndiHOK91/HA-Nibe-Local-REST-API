"""V1.0 regression coverage for REST writes, recovery, and registry migrations."""

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.nibe_local.api import NibeApiError, NibeLocalApi
from custom_components.nibe_local.coordinator import NibeCoordinator


def run(coro):
    return asyncio.run(coro)


def test_language_detection_recovers_after_temporary_api_error():
    api = NibeLocalApi(object(), host="127.0.0.1", port=8443)
    calls = []

    async def request(method, path, *, json=None):
        calls.append((method, path))
        if len(calls) == 1:
            raise NibeApiError("temporary outage")
        return {"value": {"integerValue": 2}}

    api._request = request
    run(api._ensure_language())
    assert not api._language_checked
    run(api._ensure_language())
    assert api._language_checked
    assert api._language == "de"
    run(api._ensure_language())
    assert len(calls) == 2


def test_patch_skips_identical_readback_without_writing():
    api = NibeLocalApi(object(), host="127.0.0.1", port=8443)
    api.get_point = AsyncMock(return_value={"value": {"integerValue": 1}})
    api._request = AsyncMock()
    run(api.patch_point(22077, 1))
    api._request.assert_not_awaited()


@pytest.mark.parametrize("response", [
    {"22077": "error: read only value"},
    {"22077": "error: no such param"},
    {"22077": {"value": {"isOk": False}}},
    {"22077": "unexpected"},
    {},
])
def test_patch_rejects_error_payloads_even_with_http_success(response):
    api = NibeLocalApi(object(), host="127.0.0.1", port=8443)
    api.get_point = AsyncMock(return_value={"value": {"integerValue": 0}})
    api._request = AsyncMock(return_value=response)
    with pytest.raises(NibeApiError):
        run(api.patch_point(22077, 1))
    api._request.assert_awaited_once()


def test_patch_writes_changed_value_and_preserves_zero_one_payload():
    api = NibeLocalApi(object(), host="127.0.0.1", port=8443)
    api.get_point = AsyncMock(return_value={"value": {"integerValue": 0}})
    api._request = AsyncMock(return_value={"22077": "modified"})
    run(api.patch_point(22077, 1))
    args, kwargs = api._request.await_args
    assert args == ("PATCH", "/devices/0/points")
    assert kwargs["json"][0]["integerValue"] == 1
    assert kwargs["json"][0]["variableId"] == 22077


def test_fallback_does_not_republish_cached_points_as_fresh():
    # A temporary bulk outage with an active scan backoff must mark the
    # coordinator unavailable instead of resetting connection notifications.
    fake = SimpleNamespace(
        data={"points": {"4": {"value": {"integerValue": 100}}}},
        _next_fallback_attempt=float("inf"),
        _fallback_failure_streak=1,
        api=SimpleNamespace(get_point=AsyncMock()),
    )
    with pytest.raises(NibeApiError, match="backed off"):
        run(NibeCoordinator._get_points_with_backoff(fake))
    fake.api.get_point.assert_not_awaited()


def test_fallback_all_individual_reads_fail_marks_update_unavailable():
    fake = SimpleNamespace(
        data={"points": {"4": {"value": {"integerValue": 100}}}},
        _next_fallback_attempt=0,
        _fallback_failure_streak=0,
        api=SimpleNamespace(get_point=AsyncMock(side_effect=NibeApiError("offline"))),
    )
    with pytest.raises(NibeApiError, match="no fresh values"):
        run(NibeCoordinator._get_points_with_backoff(fake))
    assert fake._fallback_failure_streak == 1
    assert fake._next_fallback_attempt > 0


def test_fallback_recovers_and_merges_fresh_values():
    new_point = {"metadata": {"variableId": 4}, "value": {"integerValue": 200}}
    fake = SimpleNamespace(
        data={"points": {"4": {"value": {"integerValue": 100}},
                         "8": {"value": {"integerValue": 42}}}},
        _next_fallback_attempt=0,
        _fallback_failure_streak=2,
        api=SimpleNamespace(get_point=AsyncMock(return_value=new_point)),
    )
    result = run(NibeCoordinator._get_points_with_backoff(fake))
    assert result["4"]["value"]["integerValue"] == 200
    assert result["8"]["value"]["integerValue"] == 42


def test_domain_migration_only_removes_obsolete_entries(monkeypatch):
    import custom_components.nibe_local as integration

    registry = MagicMock()
    existing = {
        ("binary_sensor", "entry_3098"): "binary_sensor.old_defrost",
        ("switch", "entry_4729"): "switch.old_pump",
        ("sensor", "entry_22077"): "sensor.old_aux",
        ("sensor", "entry_3935"): "sensor.old_alarm",
        ("sensor", "entry_781"): "sensor.degree_minutes",
    }
    registry.async_get_entity_id.side_effect = (
        lambda domain, platform, unique: existing.get((domain, unique))
    )
    monkeypatch.setattr(integration.er, "async_get", lambda hass: registry)
    coordinator = SimpleNamespace(
        point=lambda pid: {"metadata": {"isWritable": True}},
        entity_enabled=lambda pid: True,
        write_enabled=lambda pid: pid in {22077, 3935},
    )
    integration._remove_replaced_point_entities(
        object(), SimpleNamespace(entry_id="entry"), coordinator
    )
    removed = {call.args[0] for call in registry.async_remove.call_args_list}
    assert {"binary_sensor.old_defrost", "switch.old_pump",
            "sensor.old_aux", "sensor.old_alarm"} <= removed
    assert "sensor.degree_minutes" not in removed
