"""Entity profile selection for NIBE Local REST API."""
from __future__ import annotations

from collections.abc import Iterable

from .const import POINTS

PROFILE_STANDARD = "standard"
PROFILE_EXTENDED = "extended"
PROFILE_COMPLETE = "complete"
PROFILE_INDIVIDUAL = "individual"
ENTITY_PROFILES = (
    PROFILE_STANDARD,
    PROFILE_EXTENDED,
    PROFILE_COMPLETE,
    PROFILE_INDIVIDUAL,
)
DEFAULT_ENTITY_PROFILE = PROFILE_EXTENDED

# Standard follows the curated REST points corresponding to NIBE's default
# point selection. Only points already verified and curated for the local REST
# API are included here; unresolved candidates are intentionally excluded.
STANDARD_POINT_IDS = frozenset(
    {
        4,     # Outdoor temperature BT1
        8,     # Supply temperature BT2
        10,    # Return temperature BT3
        11,    # Hot-water top BT7
        12,    # Hot-water charge BT6
        54,    # Mean outdoor temperature BT1
        58,    # Flow BF1
        781,   # Degree minutes
        994,   # Injection temperature BT81
        997,   # Evaporator BT84
        1708,  # Calculated supply climate system 1
        1756,  # Internal auxiliary heat power
        1760,  # Internal auxiliary heat operating mode
        1975,  # Heating circulation pump GP1
        2491,  # Heat-pump return BT3
        2494,  # Condenser supply BT12
        2495,  # Hot gas BT14
        2496,  # Liquid line BT15
        2497,  # Suction gas BT17
        2766,  # Heat-pump outdoor temperature BT28
        2767,  # Evaporator BT16
        2792,  # Heating circulation pump GP1 alternative
        3095,  # Low pressure BP8
        3096,  # Compressor frequency
        3097,  # Protection mode
        3170,  # Requested compressor frequency
        3375,  # Alarm number
        7934,  # Ventilation exhaust BT20
        7935,  # Ventilation extract BT21
        7936,  # Ventilation supply BT22
        7937,  # Ventilation outdoor BT23
        7939,  # Ventilation humidity BM20
    }
)

KNOWN_POINT_IDS = frozenset(definition.point_id for definition in POINTS)


def normalize_selected_ids(values: Iterable[object] | None) -> frozenset[int]:
    """Normalize persisted point IDs while ignoring malformed values."""
    result: set[int] = set()
    for value in values or ():
        try:
            result.add(int(value))
        except (TypeError, ValueError):
            continue
    return frozenset(result)


def point_enabled(
    profile: str,
    point_id: int,
    selected_ids: Iterable[object] | None = None,
) -> bool:
    """Return whether a NIBE point belongs to the configured profile."""
    if profile == PROFILE_COMPLETE:
        return True
    if profile == PROFILE_INDIVIDUAL:
        return point_id in normalize_selected_ids(selected_ids)
    if profile == PROFILE_STANDARD:
        return point_id in STANDARD_POINT_IDS
    # Extended is also the compatibility fallback for entries without a profile.
    return point_id in KNOWN_POINT_IDS


def profile_counts(available_ids: Iterable[object]) -> dict[str, int]:
    """Return how many discovered variables are active in each automatic profile."""
    available = normalize_selected_ids(available_ids)
    return {
        PROFILE_STANDARD: len(available & STANDARD_POINT_IDS),
        PROFILE_EXTENDED: len(available & KNOWN_POINT_IDS),
        PROFILE_COMPLETE: len(available),
        PROFILE_INDIVIDUAL: len(available),
    }
