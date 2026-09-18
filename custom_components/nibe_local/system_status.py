"""Decode NIBE current-system-status bit field (point 2022)."""
from __future__ import annotations

from typing import Any

CURRENT_STATUS_STATE_OPTIONS = (
    "standby",
    "active",
    "heating",
    "hot_water",
    "cooling",
    "multiple_demands",
    "unknown",
)

# Confirmed S-series demand bits for the 32-bit "Current status" field.
CURRENT_STATUS_BIT_HEATING = 12
CURRENT_STATUS_BIT_HOT_WATER = 13
CURRENT_STATUS_BIT_COOLING = 20

# Component/activity bits corroborated by the reference VVM S320 4.13.12
# diagnostic history and the firmware's SystemOverview inputs. Keep these as
# attributes rather than treating them as the primary operating demand.
CURRENT_STATUS_BIT_COMPRESSOR = 2
CURRENT_STATUS_BIT_INTERNAL_AUX_HEAT = 10

CURRENT_STATUS_KNOWN_BITS = frozenset(
    {
        CURRENT_STATUS_BIT_COMPRESSOR,
        CURRENT_STATUS_BIT_INTERNAL_AUX_HEAT,
        CURRENT_STATUS_BIT_HEATING,
        CURRENT_STATUS_BIT_HOT_WATER,
        CURRENT_STATUS_BIT_COOLING,
    }
)


def _as_u32(value: Any) -> int | None:
    """Return a valid unsigned 32-bit integer, otherwise None."""
    try:
        numeric = int(value)
    except (TypeError, ValueError):
        return None
    if numeric < 0 or numeric > 0xFFFFFFFF:
        return None
    return numeric


def active_status_bits(value: Any) -> list[int]:
    """Return all active bit positions in the NIBE u32 status field."""
    numeric = _as_u32(value)
    if numeric is None:
        return []
    return [bit for bit in range(32) if numeric & (1 << bit)]


def decode_current_status(value: Any) -> str:
    """Return a stable Home Assistant state for NIBE point 2022.

    The visible state deliberately uses only confirmed demand bits. If no demand
    bit is set but compressor/additional heat activity is visible, return
    "active" rather than guessing the underlying demand.
    """
    numeric = _as_u32(value)
    if numeric is None:
        return "unknown"

    demands = [
        state
        for bit, state in (
            (CURRENT_STATUS_BIT_HEATING, "heating"),
            (CURRENT_STATUS_BIT_HOT_WATER, "hot_water"),
            (CURRENT_STATUS_BIT_COOLING, "cooling"),
        )
        if numeric & (1 << bit)
    ]
    if len(demands) == 1:
        return demands[0]
    if len(demands) > 1:
        return "multiple_demands"

    if numeric & (
        (1 << CURRENT_STATUS_BIT_COMPRESSOR)
        | (1 << CURRENT_STATUS_BIT_INTERNAL_AUX_HEAT)
    ):
        return "active"

    return "standby"


def current_status_attributes(value: Any) -> dict[str, Any]:
    """Return transparent bit-level diagnostics for NIBE point 2022."""
    numeric = _as_u32(value)
    if numeric is None:
        return {
            "raw_status": value,
            "hex_status": None,
            "active_bits": [],
            "unknown_active_bits": [],
            "compressor_active": False,
            "internal_additional_heat_active": False,
            "heating_active": False,
            "hot_water_active": False,
            "cooling_active": False,
        }

    active = active_status_bits(numeric)
    return {
        "raw_status": numeric,
        "hex_status": f"0x{numeric:08X}",
        "active_bits": active,
        "unknown_active_bits": [
            bit for bit in active if bit not in CURRENT_STATUS_KNOWN_BITS
        ],
        "compressor_active": bool(numeric & (1 << CURRENT_STATUS_BIT_COMPRESSOR)),
        "internal_additional_heat_active": bool(
            numeric & (1 << CURRENT_STATUS_BIT_INTERNAL_AUX_HEAT)
        ),
        "heating_active": bool(numeric & (1 << CURRENT_STATUS_BIT_HEATING)),
        "hot_water_active": bool(numeric & (1 << CURRENT_STATUS_BIT_HOT_WATER)),
        "cooling_active": bool(numeric & (1 << CURRENT_STATUS_BIT_COOLING)),
    }
