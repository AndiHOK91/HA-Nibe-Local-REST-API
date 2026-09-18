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
from custom_components.nibe_local.writable import writable_platform_for_point
from custom_components.nibe_local.profiles import (
    PROFILE_EXTENDED,
    PROFILE_INDIVIDUAL,
    write_enabled,
)


def _point(
    *,
    writable: bool,
    minimum: int = 0,
    maximum: int = 100,
    divisor: int = 1,
    variable_type: str = "integer",
    description: str = "",
) -> dict:
    return {
        "description": description,
        "metadata": {
            "isWritable": writable,
            "variableType": variable_type,
            "variableSize": "u16",
            "divisor": divisor,
            "minValue": minimum,
            "maxValue": maximum,
        },
    }


def test_write_step_includes_safe_rest_reported_writable_points() -> None:
    points = {
        "3667": _point(writable=True),  # curated number
        "3920": _point(writable=True, maximum=1),  # curated switch
        "3751": _point(writable=True, maximum=2),  # curated select, not selected
        "4": _point(writable=True, minimum=-400, maximum=800, divisor=10),
        "999997": _point(writable=True, maximum=1),  # generic switch
        "999998": _point(writable=True, minimum=-50, maximum=500, divisor=10),
        "999999": _point(
            writable=True,
            maximum=2,
            description="0=Off, 1=Auto, 2=On",
        ),
        "888888": _point(writable=True, variable_type="time"),
        "3671": _point(writable=False),
    }

    assert _supported_writable_point_ids(
        points,
        [3667, 3920, 4, 999997, 999998, 999999, 888888, 3671],
    ) == frozenset({3667, 3920, 4, 999997, 999998, 999999})

    assert writable_platform_for_point(4, points["4"]) == "number"
    assert writable_platform_for_point(999997, points["999997"]) == "switch"
    assert writable_platform_for_point(999998, points["999998"]) == "number"
    assert writable_platform_for_point(999999, points["999999"]) == "select"
    assert writable_platform_for_point(888888, points["888888"]) is None


def test_write_step_defaults_preserve_existing_behavior_and_explicit_choices() -> None:
    points = {
        "3667": _point(writable=True),
        "3920": _point(writable=True, maximum=1),
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


def test_generic_writable_points_are_never_preselected_without_explicit_choice() -> None:
    points = {
        "3667": _point(writable=True),
        "999997": _point(writable=True, maximum=1),
        "999998": _point(writable=True, minimum=-50, maximum=500, divisor=10),
    }
    selected = [3667, 999997, 999998]

    # Legacy entries keep the curated write behavior, but newly inferred generic
    # write entities always require an explicit persisted opt-in.
    assert _selected_writable_options(points, selected, None) == ["3667"]
    assert _selected_writable_options(points, selected, [999997]) == ["999997"]


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


def test_generic_write_platforms_exist_and_discovered_sensor_yields_to_them() -> None:
    assert hasattr(number, "NibeDiscoveredNumber")
    assert hasattr(select, "NibeDiscoveredSelect")
    assert hasattr(switch, "NibeDiscoveredSwitch")

    sensor_source = inspect.getsource(sensor.async_setup_entry)
    assert "generic_writable_ids" in sensor_source
    assert "writable_platform_for_point" in sensor_source
