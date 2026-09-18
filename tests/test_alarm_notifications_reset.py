"""Regression tests for NIBE alarm notifications and reset support."""
from __future__ import annotations

from types import MethodType, SimpleNamespace

import pytest

from custom_components.nibe_local.alarms import (
    alarm_notification_id,
    alarm_notification_message,
    alarm_notification_title,
    normalize_alarm,
)
from custom_components.nibe_local.api import NibeLocalApi
from custom_components.nibe_local.coordinator import NibeCoordinator
from custom_components.nibe_local.profiles import (
    PROFILE_COMPLETE,
    PROFILE_EXTENDED,
    PROFILE_INDIVIDUAL,
    PROFILE_STANDARD,
    alarm_reset_enabled,
)


def _alarm_payload() -> dict:
    return {
        "alarms": [
            {
                "alarmId": 270,
                "header": "Alarmkopf 270",
                "description": "Von der NIBE gelieferte Beschreibung 270",
                "severity": 2,
                "time": "2026-09-17 21:10:00",
                "equipName": "EB101",
            },
            {
                "alarmId": 271,
                "header": "",
                "description": "Von der NIBE gelieferte Beschreibung 271",
                "severity": 1,
                "time": "2026-09-17 21:11:00",
                "equipName": "VVM S320",
            },
        ]
    }


def test_alarm_text_uses_header_then_description() -> None:
    first = normalize_alarm(_alarm_payload()["alarms"][0], "de")
    second = normalize_alarm(_alarm_payload()["alarms"][1], "de")

    assert first["alarm_id"] == 270
    assert first["text"] == "Alarmkopf 270"
    assert first["description"] == "Von der NIBE gelieferte Beschreibung 270"

    assert second["alarm_id"] == 271
    assert second["text"] == "Von der NIBE gelieferte Beschreibung 271"


def test_alarm_notification_contains_rest_details() -> None:
    alarm = normalize_alarm(_alarm_payload()["alarms"][0], "de")

    title = alarm_notification_title(alarm, device_name="VVM S320")
    message = alarm_notification_message(alarm, german=True)

    assert title == "NIBE Alarm 270 - Alarmkopf 270"
    assert "Von der NIBE gelieferte Beschreibung 270" in message
    assert "Schweregrad" in message
    assert "EB101" in message
    assert "2026-09-17 21:10:00" in message
    assert alarm_notification_id("entry-1", alarm).endswith("_alarm_270")


def test_alarm_reset_profile_scope() -> None:
    assert alarm_reset_enabled(PROFILE_STANDARD) is False
    assert alarm_reset_enabled(PROFILE_EXTENDED) is True
    assert alarm_reset_enabled(PROFILE_COMPLETE) is True
    assert alarm_reset_enabled(PROFILE_INDIVIDUAL) is True


@pytest.mark.asyncio
async def test_reset_notifications_uses_documented_delete_endpoint() -> None:
    api = object.__new__(NibeLocalApi)
    api.device_id = "0"
    calls: list[tuple[str, str, object]] = []

    async def fake_write_request(self, method, path, *, json=None):
        calls.append((method, path, json))
        return None

    api._write_request = MethodType(fake_write_request, api)

    await api.reset_notifications()

    assert calls == [("DELETE", "/devices/0/notifications", None)]


def test_coordinator_creates_and_dismisses_alarm_notifications(monkeypatch) -> None:
    hass = SimpleNamespace(config=SimpleNamespace(language="de"))
    coordinator = object.__new__(NibeCoordinator)
    coordinator.hass = hass
    coordinator.instance_id = "entry-1"
    coordinator.device_name = "VVM S320"
    coordinator._active_alarm_notification_ids = set()

    created: list[dict] = []
    dismissed: list[str] = []

    def fake_create(hass_arg, message, *, title, notification_id):
        assert hass_arg is hass
        created.append(
            {
                "message": message,
                "title": title,
                "notification_id": notification_id,
            }
        )

    def fake_dismiss(hass_arg, notification_id):
        assert hass_arg is hass
        dismissed.append(notification_id)

    monkeypatch.setattr(
        "custom_components.nibe_local.coordinator.persistent_notification.async_create",
        fake_create,
    )
    monkeypatch.setattr(
        "custom_components.nibe_local.coordinator.persistent_notification.async_dismiss",
        fake_dismiss,
    )

    coordinator._sync_alarm_notifications(_alarm_payload())
    assert len(created) == 2
    assert {item["notification_id"] for item in created} == {
        "nibe_local_entry-1_alarm_270",
        "nibe_local_entry-1_alarm_271",
    }

    # Repeated polling must not recreate an already acknowledged HA notification.
    coordinator._sync_alarm_notifications(_alarm_payload())
    assert len(created) == 2

    coordinator._sync_alarm_notifications({"alarms": []})
    assert set(dismissed) == {
        "nibe_local_entry-1_alarm_270",
        "nibe_local_entry-1_alarm_271",
    }
