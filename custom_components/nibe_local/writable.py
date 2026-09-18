"""Safe classification of REST-reported writable NIBE points."""
from __future__ import annotations

import re
from typing import Any, Literal

from .const import POINTS

WritablePlatform = Literal["number", "select", "switch"]

_WRITABLE_PLATFORMS = frozenset({"number", "select", "switch"})
_POINT_DEFINITIONS = {definition.point_id: definition for definition in POINTS}
_DESCRIPTION_ENUM_RE = re.compile(r"^\s*(-?\d+)\s*(?:=|:)\s*(.+?)\s*$")


def api_is_writable(point: dict[str, Any] | None) -> bool:
    """Return whether the public local REST API explicitly marks a point writable."""
    return bool(((point or {}).get("metadata") or {}).get("isWritable", False))


def description_enum_map(point: dict[str, Any]) -> dict[int, str]:
    """Parse numeric enum labels supplied by the local REST point description."""
    description = str(point.get("description") or "").replace("\u00ad", "").strip()
    if not description:
        return {}

    result: dict[int, str] = {}
    for part in description.split(","):
        match = _DESCRIPTION_ENUM_RE.match(part)
        if not match:
            continue
        result[int(match.group(1))] = match.group(2).strip()
    return result


def _numeric_limits(point: dict[str, Any]) -> tuple[float, float] | None:
    """Return scaled numeric limits only when the REST metadata is unambiguous."""
    metadata = point.get("metadata") or {}
    if str(metadata.get("variableType") or "").lower() != "integer":
        return None

    divisor = metadata.get("divisor", 1)
    divisor = 1 if divisor is None else divisor
    minimum = metadata.get("minValue")
    maximum = metadata.get("maxValue")

    if not isinstance(divisor, (int, float)) or divisor <= 0:
        return None
    if not isinstance(minimum, (int, float)) or not isinstance(maximum, (int, float)):
        return None
    if minimum >= maximum:
        return None

    return float(minimum / divisor), float(maximum / divisor)


def writable_platform_for_point(
    point_id: int,
    point: dict[str, Any] | None,
) -> WritablePlatform | None:
    """Return the safe Home Assistant write platform for one REST point.

    Curated write entities keep their existing implementation. Selected unknown
    points, and curated read-only sensors, may opt into a generic write entity
    only when the public REST metadata is sufficiently explicit.

    NIBE time values intentionally remain read-only even when isWritable=true,
    because real VVM S320 tests showed HTTP 400 for unchanged time writes.
    """
    if not api_is_writable(point):
        return None

    definition = _POINT_DEFINITIONS.get(point_id)
    if definition is not None:
        if definition.platform in _WRITABLE_PLATFORMS:
            return definition.platform
        if definition.platform != "sensor":
            return None

    point = point or {}
    metadata = point.get("metadata") or {}
    if str(metadata.get("variableType") or "").lower() != "integer":
        return None

    divisor = metadata.get("divisor", 1)
    divisor = 1 if divisor is None else divisor
    minimum = metadata.get("minValue")
    maximum = metadata.get("maxValue")

    if (
        isinstance(divisor, (int, float))
        and divisor == 1
        and minimum == 0
        and maximum == 1
    ):
        return "switch"

    enum_map = description_enum_map(point)
    if len(enum_map) >= 2:
        limits = _numeric_limits(point)
        if limits is not None:
            raw_min = min(enum_map)
            raw_max = max(enum_map)
            if minimum <= raw_min <= raw_max <= maximum:
                return "select"

    if _numeric_limits(point) is not None:
        return "number"

    return None
