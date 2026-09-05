"""Base entities for NIBE Local REST."""
from __future__ import annotations

from typing import Any

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    DOMAIN,
    ENTITY_NAMING_HOME_ASSISTANT,
    ENTITY_NAMING_LOCAL_API,
    ENTITY_NAMING_TECHNICAL,
    PointDef,
)
from .coordinator import NibeCoordinator

_INTEGER_RAW_LIMITS: dict[str, tuple[int, int]] = {
    "s8": (-128, 127),
    "u8": (0, 255),
    "s16": (-32768, 32767),
    "u16": (0, 65535),
    "s32": (-2147483648, 2147483647),
    "u32": (0, 4294967295),
}


def _clean(text: str | None) -> str:
    return (text or "").replace("\u00ad", "").strip()


def _first_text(*values: Any) -> str | None:
    """Return the first non-empty textual value."""
    for value in values:
        if value in (None, ""):
            continue
        cleaned = _clean(str(value))
        if cleaned:
            return cleaned
    return None


def device_product_details(device: Any) -> dict[str, str | None]:
    """Normalize product information returned by different NIBE API versions."""
    if not isinstance(device, dict):
        device = {}

    raw_product = device.get("product")
    product = raw_product if isinstance(raw_product, dict) else {}
    product_text = raw_product if isinstance(raw_product, str) else None

    return {
        "manufacturer": _first_text(
            product.get("manufacturer"),
            product.get("manufacturerName"),
            device.get("manufacturer"),
            device.get("manufacturerName"),
        ),
        "name": _first_text(
            product.get("name"),
            product.get("productName"),
            product.get("modelName"),
            product.get("model"),
            product_text,
            device.get("productName"),
            device.get("modelName"),
            device.get("model"),
            device.get("name"),
        ),
        "software_version": _first_text(
            product.get("firmwareId"),
            product.get("firmwareVersion"),
            product.get("softwareVersion"),
            product.get("version"),
            device.get("firmwareId"),
            device.get("firmwareVersion"),
            device.get("softwareVersion"),
            device.get("version"),
        ),
        "serial_number": _first_text(
            product.get("serialNumber"),
            product.get("serial"),
            product.get("serialNo"),
            device.get("serialNumber"),
            device.get("serial"),
            device.get("serialNo"),
        ),
    }


def local_api_point_name(point: dict[str, Any]) -> str | None:
    """Return the human-readable name supplied by the local REST API."""
    metadata = point.get("metadata") or {}
    for value in (
        point.get("description"),
        point.get("name"),
        metadata.get("description"),
        metadata.get("name"),
    ):
        cleaned = _clean(str(value)) if value not in (None, "") else ""
        if cleaned:
            return cleaned
    return None


def configured_point_name(
    mode: str, point: dict[str, Any], definition: PointDef
) -> str | None:
    """Return an explicit point name for non-HA naming modes."""
    if mode == ENTITY_NAMING_HOME_ASSISTANT:
        return None
    api_name = local_api_point_name(point)
    fallback = definition.key.replace("_", " ")
    base = api_name or fallback
    if mode == ENTITY_NAMING_TECHNICAL:
        return f"{base} [ID {definition.point_id}]"
    if mode == ENTITY_NAMING_LOCAL_API:
        return base
    return None


def point_value(point: dict[str, Any]) -> dict[str, Any]:
    """Return the value object.

    Current NIBE firmware uses the key "value". Older documentation/examples
    may refer to it as "datavalue", so keep both for API compatibility.
    """
    return point.get("value") or point.get("datavalue") or {}


def raw_value(point: dict[str, Any]) -> int | str | None:
    dv = point_value(point)
    sv = dv.get("stringValue")
    if sv not in (None, ""):
        return sv
    return dv.get("integerValue")


def raw_value_is_sentinel(point: dict[str, Any]) -> bool:
    """Return whether an integer value is a NIBE-style invalid limit sentinel.

    NIBE may expose an unavailable integer value as the numeric limit of the
    underlying storage type, for example -32768 for s16 or 65535 for u16,
    while still reporting isOk=true. Preserve a limit value when the REST
    metadata explicitly declares that exact limit as valid.
    """
    raw = raw_value(point)
    if not isinstance(raw, int) or isinstance(raw, bool):
        return False

    metadata = point.get("metadata") or {}
    variable_size = metadata.get("variableSize")
    limits = _INTEGER_RAW_LIMITS.get(str(variable_size))
    if limits is None:
        return False

    minimum, maximum = limits
    if str(variable_size).startswith("s") and raw == minimum:
        return metadata.get("minValue") != raw
    if str(variable_size).startswith("u") and raw == maximum:
        return metadata.get("maxValue") != raw
    return False


def scaled_value(point: dict[str, Any]) -> int | float | str | None:
    raw = raw_value(point)
    if raw_value_is_sentinel(point):
        return None
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


def entity_unique_id(coordinator: NibeCoordinator, suffix: str | int) -> str:
    """Return a config-entry-scoped stable entity unique ID."""
    return f"{coordinator.instance_id}_{suffix}"


def coordinator_device_info(coordinator: NibeCoordinator) -> DeviceInfo:
    """Build the shared Home Assistant device info for coordinator entities."""
    details = device_product_details((coordinator.data or {}).get("device", {}))
    serial = details["serial_number"] or str(coordinator.api.device_id)
    name = details["name"] or "NIBE API"
    return DeviceInfo(
        identifiers={(DOMAIN, str(serial))},
        manufacturer=details["manufacturer"] or "NIBE",
        name=name,
        model=details["name"],
        sw_version=details["software_version"],
    )


class NibePointEntity(CoordinatorEntity[NibeCoordinator]):
    """Base entity for one NIBE point."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: NibeCoordinator, definition: PointDef) -> None:
        super().__init__(coordinator)
        self.definition = definition
        self._attr_unique_id = entity_unique_id(coordinator, definition.point_id)
        explicit_name = configured_point_name(
            coordinator.entity_naming, coordinator.point(definition.point_id) or {}, definition
        )
        if explicit_name is None:
            self._attr_translation_key = definition.key
        else:
            self._attr_translation_key = None
            self._attr_name = explicit_name
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
        if raw_value_is_sentinel(point):
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
            "raw_value_is_sentinel": raw_value_is_sentinel(point),
            "divisor": md.get("divisor"),
            "decimal": md.get("decimal"),
            "min_value_raw": md.get("minValue"),
            "max_value_raw": md.get("maxValue"),
        }
