"""Regression tests for per-point write selection in the Individual profile."""

import inspect

from custom_components.nibe_local import number, select, sensor, switch
from custom_components.nibe_local.config_flow import (
    NibeLocalConfigFlow,
    NibeLocalOptionsFlow,
    _selected_writable_options,
    _supported_writable_point_ids,
    _write_selection_schema,
)
from custom_components.nibe_local.const import CONF_SELECTED_WRITABLE_POINT_IDS
from custom_components.nibe_local.profiles import (
    PROFILE_EXTENDED,
    PROFILE_INDIVIDUAL,
    write_enabled,
)


def _point(*, writable: bool) -> dict:
    return {"metadata": {"isWritable": writable}}


def test_write_step_only_offers_selected_supported_writable_points() -> None:
    points = {
        "3667": _point(writable=True),   # curated number
        "3920": _point(writable=True),   # curated switch
        "3751": _point(writable=True),   # curated select, not selected below
        "4": _point(writable=True),      # curated sensor: never generic writable
        "999999": _point(writable=True), # unknown: stays read-only by design
        "3671": _point(writable=False),  # curated number but API says read-only
    }

    assert _supported_writable_point_ids(
        points,
        [3667, 3920, 4, 999999, 3671],
    ) == frozenset({3667, 3920})


def test_write_step_defaults_preserve_existing_behavior_and_explicit_choices() -> None:
    points = {
        "3667": _point(writable=True),
        "3920": _point(writable=True),
    }
    selected = [3667, 3920]

    # No persisted setting means a pre-feature Individual entry: keep both
    # writable until the user explicitly changes the new selector.
    assert _selected_writable_options(points, selected, None) == ["3667", "3920"]
    assert _selected_writable_options(points, selected, [3667]) == ["3667"]
    assert _selected_writable_options(points, selected, []) == []

    schema = _write_selection_schema(points, selected, [3920])
    validated = schema({})
    assert validated[CONF_SELECTED_WRITABLE_POINT_IDS] == ["3920"]


def test_write_permission_only_applies_to_individual_profile() -> None:
    assert write_enabled(PROFILE_EXTENDED, 3667, []) is True

    # Legacy Individual entries without the new setting keep old behavior.
    assert write_enabled(PROFILE_INDIVIDUAL, 3667, None) is True

    assert write_enabled(PROFILE_INDIVIDUAL, 3667, [3667]) is True
    assert write_enabled(PROFILE_INDIVIDUAL, 3920, [3667]) is False
    assert write_enabled(PROFILE_INDIVIDUAL, 3920, []) is False


def test_config_and_options_flows_insert_write_step_after_entity_selection() -> None:
    config_source = inspect.getsource(NibeLocalConfigFlow.async_step_entity_selection)
    options_source = inspect.getsource(NibeLocalOptionsFlow.async_step_entity_selection)

    assert "async_step_write_selection" in config_source
    assert "async_step_write_selection" in options_source


def test_write_platforms_and_read_only_fallback_respect_preference() -> None:
    assert "coordinator.write_enabled" in inspect.getsource(number.async_setup_entry)
    assert "coordinator.write_enabled" in inspect.getsource(select.async_setup_entry)
    assert "coordinator.write_enabled" in inspect.getsource(switch.async_setup_entry)

    sensor_source = inspect.getsource(sensor.async_setup_entry)
    assert "read_only_known_write_ids" in sensor_source
    assert "coordinator.write_enabled" in sensor_source
