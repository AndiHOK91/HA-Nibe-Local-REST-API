"""Regression tests for optional-equipment status tracking in the options flow."""

from custom_components.nibe_local.config_flow import (
    CONF_DETECTED_EQUIPMENT,
    _equipment_options_default,
    _equipment_status_suffix,
)
from custom_components.nibe_local.equipment import (
    CONF_EQUIPMENT,
    EQUIPMENT_BE6,
    EQUIPMENT_BE7,
    EQUIPMENT_VENTILATION,
)


def _suffix(value, *, detected=(), configured=(), previous_detected=None):
    return _equipment_status_suffix(
        value,
        german=True,
        detected=detected,
        configured=configured,
        previous_detected=previous_detected,
        detection_available=True,
        options_mode=True,
    )


def test_first_detection_without_baseline_is_only_marked_detected() -> None:
    assert _suffix(
        EQUIPMENT_BE6,
        detected=[EQUIPMENT_BE6],
        configured=[EQUIPMENT_BE6],
        previous_detected=None,
    ) == " (erkannt)"


def test_existing_detected_equipment_is_marked_already_added() -> None:
    assert _suffix(
        EQUIPMENT_BE6,
        detected=[EQUIPMENT_BE6],
        configured=[EQUIPMENT_BE6],
        previous_detected=[EQUIPMENT_BE6],
    ) == " (erkannt – bereits hinzugefügt)"


def test_newly_detected_be7_is_marked_new_and_preselected() -> None:
    current = {
        CONF_EQUIPMENT: [EQUIPMENT_BE6],
        CONF_DETECTED_EQUIPMENT: [EQUIPMENT_BE6],
    }
    detected = [EQUIPMENT_BE6, EQUIPMENT_BE7]

    assert _suffix(
        EQUIPMENT_BE7,
        detected=detected,
        configured=current[CONF_EQUIPMENT],
        previous_detected=current[CONF_DETECTED_EQUIPMENT],
    ) == " (erkannt – neu hinzugefügt)"
    assert _equipment_options_default(
        current, detected, detection_available=True
    ) == [EQUIPMENT_BE6, EQUIPMENT_BE7]


def test_deliberately_unselected_detected_equipment_is_not_readded() -> None:
    current = {
        CONF_EQUIPMENT: [EQUIPMENT_BE6],
        CONF_DETECTED_EQUIPMENT: [EQUIPMENT_BE6, EQUIPMENT_BE7],
    }
    detected = [EQUIPMENT_BE6, EQUIPMENT_BE7]

    assert _suffix(
        EQUIPMENT_BE7,
        detected=detected,
        configured=current[CONF_EQUIPMENT],
        previous_detected=current[CONF_DETECTED_EQUIPMENT],
    ) == " (erkannt – nicht hinzugefügt)"
    assert _equipment_options_default(
        current, detected, detection_available=True
    ) == [EQUIPMENT_BE6]


def test_no_longer_detected_equipment_stays_selected_and_is_marked() -> None:
    current = {
        CONF_EQUIPMENT: [EQUIPMENT_BE6, EQUIPMENT_VENTILATION],
        CONF_DETECTED_EQUIPMENT: [EQUIPMENT_BE6, EQUIPMENT_VENTILATION],
    }
    detected = [EQUIPMENT_BE6]

    assert _suffix(
        EQUIPMENT_VENTILATION,
        detected=detected,
        configured=current[CONF_EQUIPMENT],
        previous_detected=current[CONF_DETECTED_EQUIPMENT],
    ) == " (nicht mehr erkannt – weiterhin hinzugefügt)"
    assert _equipment_options_default(
        current, detected, detection_available=True
    ) == [EQUIPMENT_BE6, EQUIPMENT_VENTILATION]


def test_legacy_entry_without_equipment_uses_detection_not_all_options() -> None:
    assert _equipment_options_default(
        {}, [EQUIPMENT_BE6], detection_available=True
    ) == [EQUIPMENT_BE6]


def test_detection_failure_never_enables_equipment_for_legacy_entry() -> None:
    assert _equipment_options_default(
        {}, [EQUIPMENT_BE6, EQUIPMENT_BE7], detection_available=False
    ) == []
