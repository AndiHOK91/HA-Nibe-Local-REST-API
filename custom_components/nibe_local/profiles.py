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

# Curated base set aligned with the previously verified NIBE default selection.
STANDARD_POINT_IDS = frozenset(
    {
        4, 8, 10, 11, 12, 54, 58, 781, 994, 997, 1708, 1756, 1760, 1975,
        2491, 2494, 2495, 2496, 2497, 2766, 2767, 2792, 3095, 3096, 3097,
        3170, 3375, 7934, 7935, 7936, 7937, 7939,
    }
)

# Additional default-selection points directly verified through the local REST API.
STANDARD_VERIFIED_EXTRA_POINT_IDS = frozenset(
    {
        29,     # Room sensor climate system 1 BT50
        91,     # Additional heat BT63
        10894,  # Hot-water start BT5
    }
)
STANDARD_PROFILE_POINT_IDS = STANDARD_POINT_IDS | STANDARD_VERIFIED_EXTRA_POINT_IDS

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
        return point_id in STANDARD_PROFILE_POINT_IDS
    # Extended is also the compatibility fallback for entries without a profile.
    return point_id in KNOWN_POINT_IDS


def profile_counts(available_ids: Iterable[object]) -> dict[str, int]:
    """Return how many discovered variables are active in each automatic profile."""
    available = normalize_selected_ids(available_ids)
    return {
        PROFILE_STANDARD: len(available & STANDARD_PROFILE_POINT_IDS),
        PROFILE_EXTENDED: len(available & KNOWN_POINT_IDS),
        PROFILE_COMPLETE: len(available),
        PROFILE_INDIVIDUAL: len(available),
    }
