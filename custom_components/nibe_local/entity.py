"""Base entities for NIBE Local REST."""
from __future__ import annotations

from typing import Any

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, POINT_BY_ID, PointDef
from .coordinator import NibeCoordinator


# Backward-compatible export for existing tests and external imports. Entity names
# are now resolved through Home Assistant translations via translation_key.
FRIENDLY_NAMES = {point_id: definition.key for point_id, definition in POINT_BY_ID.items()}


def _clean(text: str | None) -> str:
    return (text or "").replace("\u00ad", "").strip()


def point_value(point: dict[str, Any]) -> dict[str, Any]:
    """Return the value object.

    Current NIBE firmware uses the key "value". Older documentation/examples
    may refer to it as "datavalue", so keep both for compatibility.
    """
    return point.get("value") or point.get("datavalue") or {}


def raw_value(point: dict[str, Any]) -> int | str | None:
    dv = point_value(point)
    sv = dv.get("stringValue")
    if sv not in (None, ""):
        return sv
    return dv.get("integerValue")


def scaled_value(point: dict[str, Any]) -> int | float | str | None:
    raw = raw_value(point)
    if not isinstance(raw, (int, float)):
        return raw
    md = point.get("metadata") or {}
    divisor = md.get("divisor") or 1
    try:
        value = raw / divisor
    except (TypeError, ZeroDivisionError):
        value = raw
    decimal = md.get("decimal")
    if isinstance(decimal, int) and decimal >= 0:
        value = round(value, decimal)
    if isinstance(value, float) and value.is_integer():
        return int(value)
    return value


def to_raw(point: dict[str, Any], value: float) -> int:
    md = point.get("metadata") or {}
    divisor = md.get("divisor") or 1
    return int(round(value * divisor))


def coordinator_device_info(coordinator: NibeCoordinator) -> DeviceInfo:
    """Build the shared Home Assistant device info for coordinator entities."""
    device = (coordinator.data or {}).get("device", {})
    product = device.get("product") or {}
    serial = product.get("serialNumber") or coordinator.api.device_id
    return DeviceInfo(
        identifiers={(DOMAIN, str(serial))},
        manufacturer=product.get("manufacturer") or "NIBE",
        name=product.get("name") or "NIBE VVM S320",
        model=product.get("name"),
        sw_version=product.get("firmwareId"),
    )


class NibePointEntity(CoordinatorEntity[NibeCoordinator]):
    """Base entity for one NIBE point."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: NibeCoordinator, definition: PointDef) -> None:
        super().__init__(coordinator)
        self.definition = definition
        self._attr_unique_id = f"{coordinator.api.device_id}_{definition.point_id}"
        self._attr_translation_key = definition.key
        if definition.diagnostic:
            self._attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def point(self) -> dict[str, Any] | None:
        return self.coordinator.point(self.definition.point_id)

    @property
    def available(self) -> bool:
        point = self.point
        if not self.coordinator.last_update_success or not point:
            return False
        return bool(point_value(point).get("isOk", True))

    @property
    def device_info(self) -> DeviceInfo:
        return coordinator_device_info(self.coordinator)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        point = self.point or {}
        md = point.get("metadata") or {}
        return {
            "point_id": self.definition.point_id,
            "group": self.definition.group,
            "description": _clean(point.get("description")),
            "variable_type": md.get("variableType"),
            "variable_size": md.get("variableSize"),
            "is_writable": md.get("isWritable"),
            "modbus_register_type": md.get("modbusRegisterType"),
            "modbus_register_id": md.get("modbusRegisterID"),
            "raw_value": raw_value(point),
            "divisor": md.get("divisor"),
            "decimal": md.get("decimal"),
            "min_value_raw": md.get("minValue"),
            "max_value_raw": md.get("maxValue"),
        }
