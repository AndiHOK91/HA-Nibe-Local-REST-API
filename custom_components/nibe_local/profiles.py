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

# Minimal intentionally contains only the current core operating state and
# the most important temperatures. Controls, comfort functions, hydraulic
# values and detailed compressor data start with Standard.
MINIMAL_POINT_IDS = frozenset(
    {
        4,     # Outdoor temperature BT1
        8,     # Supply temperature BT2
        10,    # Return temperature BT3
        11,    # Hot-water top BT7
        12,    # Hot-water charge BT6
        116,   # Hot-water outlet BT70
        158,   # Room temperature BT50
        1758,  # Operating priority
        2500,  # Compressor status
        3096,  # Compressor frequency
        4064,  # Operating mode status
    }
)

# Normal Home Assistant use: Minimal plus the controls, calculated values,
# hydraulic/energy data, compressor operating values, hot-water functions,
# heating/cooling settings, selected defrost values and common ventilation.
# Detailed alarm and EEV/service values remain Extended-only.
STANDARD_POINT_IDS = MINIMAL_POINT_IDS | frozenset(
    {
        54, 58, 781,
        834, 839, 840,
        1708, 1716, 1755, 1756, 1829, 1942, 1975, 2002, 2022,
        2491, 2494, 2501, 2505, 2506, 2507,
        25165, 25166,
        2657, 2683, 2685, 2691, 2695, 2729, 2766, 2767,
        3095, 3096, 3097, 3098, 3101, 3138, 3170, 3252, 3353, 3354, 3375,
        3667, 3671, 3697,
        3699, 3700, 3701, 3703, 3704, 3705, 3706, 3707, 3708,
        3751, 3830, 3920, 3921, 4030, 4040, 4564, 5025, 5033, 8060,
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


def profile_counts(available_ids: Iterable[object]) -> dict[str, int]:
    """Return how many discovered variables are active in each automatic profile."""
    available = normalize_selected_ids(available_ids)
    return {
        PROFILE_MINIMAL: len(available & MINIMAL_POINT_IDS),
        PROFILE_STANDARD: len(available & STANDARD_POINT_IDS),
        PROFILE_EXTENDED: len(available & KNOWN_POINT_IDS),
        PROFILE_COMPLETE: len(available),
        PROFILE_INDIVIDUAL: len(available),
    }
