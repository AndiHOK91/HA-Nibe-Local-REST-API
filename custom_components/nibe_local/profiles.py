"""Entity profile selection for NIBE Local REST API."""
from __future__ import annotations

from collections.abc import Iterable

from .const import POINTS

PROFILE_MINIMAL = "minimal"
PROFILE_STANDARD = "standard"
PROFILE_EXTENDED = "extended"
PROFILE_COMPLETE = "complete"
PROFILE_INDIVIDUAL = "individual"
ENTITY_PROFILES = (
    PROFILE_MINIMAL,
    PROFILE_STANDARD,
    PROFILE_EXTENDED,
    PROFILE_COMPLETE,
    PROFILE_INDIVIDUAL,
)
DEFAULT_ENTITY_PROFILE = PROFILE_EXTENDED

# Small, dashboard-oriented core: operating state, main temperatures,
# hot water, compressor, flow and the most useful user controls.
MINIMAL_POINT_IDS = frozenset(
    {
        4, 8, 10, 11, 12, 58, 781, 1758, 1975, 2022,
        2500, 2657, 3096, 3101, 3697, 3751, 3920, 3921,
        4030, 4064, 4564,
    }
)

# Normal Home Assistant use: the minimal set plus calculated targets,
# heating/cooling curves, hot-water controls, energy, compressor details,
# defrost state and common ventilation values.
STANDARD_POINT_IDS = MINIMAL_POINT_IDS | frozenset(
    {
        54, 158, 1708, 1716, 1829, 1942, 2002, 2491, 2494,
        2505, 2506, 2507, 25165, 25166, 2683, 2685, 2691,
        2695, 2729, 2766, 2767, 2792, 3095, 3097, 3098,
        3138, 3170, 3252, 3353, 3354, 3667, 3671, 3699,
        3700, 3701, 3703, 3704, 3705, 3706, 3707, 3708,
        3830, 4040, 5025, 5033, 8060,
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
    if profile == PROFILE_MINIMAL:
        return point_id in MINIMAL_POINT_IDS
    if profile == PROFILE_STANDARD:
        return point_id in STANDARD_POINT_IDS
    # Extended is also the compatibility fallback for pre-0.9 entries.
    return point_id in KNOWN_POINT_IDS
