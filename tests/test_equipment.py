"""Regression tests for optional-equipment detection and filtering."""

from custom_components.nibe_local.equipment import (
    ALL_EQUIPMENT,
    EQUIPMENT_BE6,
    EQUIPMENT_BE7,
    EQUIPMENT_HOT_WATER_CIRCULATION,
    EQUIPMENT_VENTILATION,
    FORCED_CONTROL_POINT_IDS,
    detect_equipment,
    filter_points_for_equipment,
    normalize_equipment,
    point_allowed_by_equipment,
)


def _point(value=0, *, name=None, register_type=None, register_id=None):
    metadata = {}
    if name is not None:
        metadata["name"] = name
    if register_type is not None:
        metadata["modbusRegisterType"] = register_type
    if register_id is not None:
        metadata["modbusRegisterID"] = register_id
    return {
        "metadata": metadata,
        "value": {"integerValue": value, "stringValue": ""},
    }


def test_legacy_entries_keep_all_equipment_enabled() -> None:
    assert normalize_equipment(None) == ALL_EQUIPMENT
    assert normalize_equipment([], legacy_default=False) == frozenset()


def test_detects_dump_equipment_without_menu_requests() -> None:
    points = {
        "5200": _point(1, name="Energiezähler Impuls (BE6/BF2)"),
        "7048": _point(0, name="Energiezähler Impuls (BE7/BF3)"),
        "3959": _point(3, name="AUX-Relais (X27)"),
        # ERS accessory 7933 is menu-only on the captured firmware; a live
        # ERS temperature point provides the safe /points fallback.
        "7934": _point(278, name="Abluft (AZ30-BT20)"),
    }
    assert detect_equipment(points) == frozenset(
        {
            EQUIPMENT_BE6,
            EQUIPMENT_VENTILATION,
            EQUIPMENT_HOT_WATER_CIRCULATION,
        }
    )


def test_be6_detection_uses_rest_accessory_flag_5200() -> None:
    assert EQUIPMENT_BE6 in detect_equipment(
        {"5200": _point(1, name="Energiezähler Impuls (BE6/BF2)")}
    )
    assert EQUIPMENT_BE6 not in detect_equipment(
        {
            "5200": _point(0, name="Energiezähler Impuls (BE6/BF2)"),
            "829": _point(123, name="Energiezähler Impuls (BE6)"),
        }
    )
    assert EQUIPMENT_BE6 not in detect_equipment(
        {"829": _point(123, name="Energiezähler Impuls (BE6)")}
    )


def test_be7_detection_uses_rest_accessory_flag_7048() -> None:
    assert EQUIPMENT_BE7 in detect_equipment(
        {"7048": _point(1, name="Energiezähler Impuls (BE7/BF3)")}
    )
    assert EQUIPMENT_BE7 not in detect_equipment(
        {"7048": _point(0, name="Energiezähler Impuls (BE7/BF3)")}
    )


def test_be7_detection_ignores_modbus_metadata() -> None:
    points = {
        "99992": _point(
            1234,
            name="Energy meter BE7",
            register_type="MODBUS_INPUT_REGISTER",
            register_id=396,
        )
    }
    assert EQUIPMENT_BE7 not in detect_equipment(points)


def test_detects_other_ers_models_by_accessory_name() -> None:
    points = {
        "99991": _point(1, name="ERS S10 1"),
    }
    assert EQUIPMENT_VENTILATION in detect_equipment(points)


def test_explicit_ers_accessory_off_wins_over_runtime_fallback() -> None:
    points = {
        "99991": _point(0, name="ERS S10 1"),
        "7934": _point(278, name="Abluft (AZ30-BT20)"),
    }
    assert EQUIPMENT_VENTILATION not in detect_equipment(points)


def test_forced_control_menu_is_always_excluded() -> None:
    assert len(FORCED_CONTROL_POINT_IDS) == 21
    for point_id in FORCED_CONTROL_POINT_IDS:
        assert not point_allowed_by_equipment(point_id, ALL_EQUIPMENT, _point(1))


def test_ventilation_points_require_ventilation_selection() -> None:
    assert not point_allowed_by_equipment(3830, [], _point(3, name="Ventilationsmodus"))
    assert point_allowed_by_equipment(
        3830,
        [EQUIPMENT_VENTILATION],
        _point(3, name="Ventilationsmodus"),
    )


def test_complete_hot_water_circulation_schedule_is_filtered_as_one_group() -> None:
    circulation_ids = (1829, 3710, 3711, 7849, 7852, 12394, 21904, 21938)
    for point_id in circulation_ids:
        assert not point_allowed_by_equipment(point_id, [], _point(1))
        assert point_allowed_by_equipment(
            point_id,
            [EQUIPMENT_HOT_WATER_CIRCULATION],
            _point(1),
        )


def test_x27_configuration_remains_read_only_visible_information() -> None:
    # 3959 is intentionally not part of the circulation filter. It is not a
    # curated writable entity, so Complete can still show it as a read-only
    # discovered sensor even when X27 is assigned to another function.
    assert point_allowed_by_equipment(3959, [], _point(3, name="AUX-Relais (X27)"))


def test_filter_removes_forced_and_unselected_optional_points() -> None:
    points = {
        "4": _point(222, name="Outdoor temperature"),
        "3754": _point(1, name="Zwangssteuerung aktivieren"),
        "3830": _point(3, name="Ventilationsmodus"),
        "3710": _point(60, name="Betriebszeit"),
        "829": _point(100, name="Energiezähler Impuls (BE6)"),
    }
    filtered = filter_points_for_equipment(points, [EQUIPMENT_BE6])
    assert set(filtered) == {"4", "829"}
