"""Regression tests for optional prioritised external auxiliary heat."""

from custom_components.nibe_local.equipment import (
    EQUIPMENT_OPTIONS,
    EQUIPMENT_PRIORITIZED_EXTERNAL_AUX_HEAT,
    detect_equipment,
    point_allowed_by_equipment,
)

POINT_ID = 1186


def _point(value: int) -> dict:
    return {
        "description": "Permit prioritised additional heat",
        "metadata": {"variableId": POINT_ID},
        "value": {"integerValue": value, "stringValue": ""},
    }


def test_prioritized_external_aux_heat_is_explicit_setup_option() -> None:
    assert EQUIPMENT_PRIORITIZED_EXTERNAL_AUX_HEAT in EQUIPMENT_OPTIONS
    assert not point_allowed_by_equipment(POINT_ID, ())
    assert point_allowed_by_equipment(
        POINT_ID, (EQUIPMENT_PRIORITIZED_EXTERNAL_AUX_HEAT,)
    )


def test_prioritized_external_aux_heat_is_not_auto_detected_from_point() -> None:
    assert EQUIPMENT_PRIORITIZED_EXTERNAL_AUX_HEAT not in detect_equipment(
        {str(POINT_ID): _point(0)}
    )
    assert EQUIPMENT_PRIORITIZED_EXTERNAL_AUX_HEAT not in detect_equipment(
        {str(POINT_ID): _point(1)}
    )
