"""Equipment detection and point filtering for NIBE Local REST API."""
from __future__ import annotations

from collections.abc import Iterable
from typing import Any

CONF_EQUIPMENT = "equipment"

EQUIPMENT_BE6 = "be6"
EQUIPMENT_BE7 = "be7"
EQUIPMENT_VENTILATION = "ventilation"
EQUIPMENT_HOT_WATER_CIRCULATION = "hot_water_circulation"
EQUIPMENT_OPTIONS = (
    EQUIPMENT_BE6,
    EQUIPMENT_BE7,
    EQUIPMENT_VENTILATION,
    EQUIPMENT_HOT_WATER_CIRCULATION,
)
ALL_EQUIPMENT = frozenset(EQUIPMENT_OPTIONS)

# Menu 7.5.3 "Zwangssteuerung" is a service/forced-control menu. These points
# must never be exposed by the integration, including Complete/Individual.
FORCED_CONTROL_POINT_IDS = frozenset(
    {
        3754,
        3763,
        3764,
        3765,
        3766,
        3767,
        3768,
        3817,
        4083,
        5044,
        5202,
        5925,
        7957,
        7958,
        7959,
        7960,
        7961,
        7962,
        22155,
        28181,
        55038,
    }
)

# Accessory-selection points observed in menu 7.2.1. Name-based detection below
# additionally supports other ERS generations/models without hard-coding IDs.
ERS_ACCESSORY_POINT_IDS = frozenset(
    {7933, 15090, 15150, 15210, 21295, 21351, 21407, 21463}
)

# Strong live-runtime hints for an installed ERS. The accessory-selection
# variables are menu-visible on some firmware and therefore may be absent from
# the normal /points response. These live variables provide a safe fallback
# without querying /menu or /menuchain during Home Assistant setup.
ERS_RUNTIME_HINT_POINT_IDS = frozenset({7934, 7935, 7936, 7937, 7939, 7969, 7970})

# Known ERS/ventilation variables from the curated REST point set.
VENTILATION_POINT_IDS = frozenset(
    {
        248,
        249,
        3830,
        3841,
        3842,
        3843,
        3844,
        4040,
        4041,
        5958,
        7933,
        7934,
        7935,
        7936,
        7937,
        7939,
        7969,
        7970,
        15048,
        15049,
        15050,
        15060,
        15090,
        15150,
        15210,
        15632,
        21295,
        21351,
        21407,
        21463,
        55061,
        60432,
        63586,
    }
)

# Hot-water circulation points directly exposed by the local REST API:
# current GP11 state, cycle times, and the three available schedule periods.
HOT_WATER_CIRCULATION_POINT_IDS = frozenset(
    {
        1829,
        3710,
        3711,
        7849,
        7850,
        7851,
        7852,
        7853,
        7854,
    }
)

# 5200 and 7048 are REST variable IDs from menu 7.2.1
# "Zubehör hinzufügen/entfernen":
#   5200 = Energiezähler Impuls (BE6/BF2)
#   7048 = Energiezähler Impuls (BE7/BF3)
# Their value is the authoritative equipment-detection signal. Modbus metadata
# embedded in REST point metadata is intentionally not used for detection.
BE6_POINT_IDS = frozenset({829, 5200})
BE7_POINT_IDS = frozenset({7048})


def normalize_equipment(
    values: Iterable[object] | None,
    *,
    legacy_default: bool = True,
) -> frozenset[str]:
    """Normalize persisted equipment values.

    Existing config entries created before this option existed keep the former
    behavior by treating all equipment groups as enabled.
    """
    if values is None:
        return ALL_EQUIPMENT if legacy_default else frozenset()
    if isinstance(values, str):
        values = (values,)
    return frozenset(str(value) for value in values if str(value) in ALL_EQUIPMENT)


def _raw_value(point: dict[str, Any] | None) -> int | float | str | None:
    value: Any
    if not isinstance(point, dict):
        return None
    value = point.get("value") or point.get("datavalue") or {}
    string_value = value.get("stringValue")
    if string_value not in (None, ""):
        return string_value
    return value.get("integerValue")


def _numeric_value(point: dict[str, Any] | None) -> int | float | None:
    value = _raw_value(point)
    if isinstance(value, (int, float)):
        return value
    try:
        return float(str(value).strip())
    except (TypeError, ValueError):
        return None


def _point_text(point: dict[str, Any] | None) -> str:
    if not isinstance(point, dict):
        return ""
    metadata = point.get("metadata") or {}
    values = (
        point.get("description"),
        point.get("name"),
        metadata.get("description"),
        metadata.get("name"),
    )
    return " ".join(str(value) for value in values if value not in (None, "")).lower()


def _is_enabled_flag(point: dict[str, Any] | None) -> bool:
    return _numeric_value(point) == 1


def _is_ers_accessory(point_id: int, point: dict[str, Any] | None) -> bool:
    if point_id in ERS_ACCESSORY_POINT_IDS:
        return True
    text = _point_text(point)
    return any(
        marker in text
        for marker in (
            "ers ",
            "ers-",
            "ab-/zuluft",
            "ab-/zuluftmodul",
            "abluft-/zuluft",
            "supply/exhaust air module",
        )
    )


def _looks_like_ventilation_point(point: dict[str, Any] | None) -> bool:
    text = _point_text(point)
    return any(
        marker in text
        for marker in (
            "lüft.wärmet",
            "lüftungswärmet",
            "ventilation",
            "abluft",
            "fortluft",
            "zuluft",
            "ers ",
            "ers-",
        )
    )


def detect_equipment(points: dict[str, Any]) -> frozenset[str]:
    """Detect installed optional equipment from REST point values only."""
    detected: set[str] = set()

    if _is_enabled_flag(points.get("5200")):
        detected.add(EQUIPMENT_BE6)

    if _is_enabled_flag(points.get("7048")):
        detected.add(EQUIPMENT_BE7)

    ers_accessory_seen = False
    for point_id, point in points.items():
        try:
            numeric_id = int(point_id)
        except (TypeError, ValueError):
            continue
        if not _is_ers_accessory(numeric_id, point):
            continue
        ers_accessory_seen = True
        if _is_enabled_flag(point):
            detected.add(EQUIPMENT_VENTILATION)
            break

    if (
        EQUIPMENT_VENTILATION not in detected
        and not ers_accessory_seen
        and any(str(point_id) in points for point_id in ERS_RUNTIME_HINT_POINT_IDS)
    ):
        detected.add(EQUIPMENT_VENTILATION)

    x27 = points.get("3959")
    x27_value = _raw_value(x27)
    x27_text = str(x27_value or "").lower()
    if (
        _numeric_value(x27) == 3
        or "bw-zirk" in x27_text
        or "hot water circulation" in x27_text
    ):
        detected.add(EQUIPMENT_HOT_WATER_CIRCULATION)

    return frozenset(detected)


def point_allowed_by_equipment(
    point_id: int,
    equipment: Iterable[object] | None,
    point: dict[str, Any] | None = None,
) -> bool:
    """Return whether a point may be exposed for the selected equipment."""
    if point_id in FORCED_CONTROL_POINT_IDS:
        return False

    enabled = normalize_equipment(equipment)
    text = _point_text(point)

    if point_id in BE6_POINT_IDS or "be6" in text:
        return EQUIPMENT_BE6 in enabled
    if point_id in BE7_POINT_IDS or "be7" in text:
        return EQUIPMENT_BE7 in enabled
    if point_id in HOT_WATER_CIRCULATION_POINT_IDS:
        return EQUIPMENT_HOT_WATER_CIRCULATION in enabled
    if point_id in VENTILATION_POINT_IDS or _looks_like_ventilation_point(point):
        return EQUIPMENT_VENTILATION in enabled

    return True


def filter_points_for_equipment(
    points: dict[str, Any], equipment: Iterable[object] | None
) -> dict[str, Any]:
    """Filter discovered points for setup/selection/preview purposes."""
    filtered: dict[str, Any] = {}
    for point_id, point in points.items():
        try:
            numeric_id = int(point_id)
        except (TypeError, ValueError):
            continue
        if point_allowed_by_equipment(numeric_id, equipment, point):
            filtered[str(point_id)] = point
    return filtered
