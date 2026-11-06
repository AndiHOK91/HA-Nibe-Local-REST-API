"""All curated defrost and EEV diagnostics are present in Extended."""
import pytest

from custom_components.nibe_local.const import POINTS
from custom_components.nibe_local.profiles import (
    DEFROST_EXTENDED_POINT_IDS,
    EXTENDED_PROFILE_POINT_IDS,
    PROFILE_EXTENDED,
    PROFILE_COMPLETE,
    PROFILE_INDIVIDUAL,
    point_enabled,
)

# Explicit user-facing defrost diagnostics; retain these even if the automatic
# Extended exclusions change in a later release.
DEFROST_CORE_IDS = {3098, 840, 841, 8052, 8060, 22268}


def test_defrost_diagnostics_are_all_in_extended():
    definitions = {
        definition.point_id
        for definition in POINTS
        if definition.group == "eev_defrost" or "defrost" in definition.key
    }
    assert DEFROST_CORE_IDS <= definitions
    assert DEFROST_EXTENDED_POINT_IDS == definitions
    assert definitions <= EXTENDED_PROFILE_POINT_IDS
    assert all(point_enabled(PROFILE_EXTENDED, point_id) for point_id in definitions)
    assert all(point_enabled(PROFILE_COMPLETE, point_id) for point_id in definitions)


@pytest.mark.parametrize("point_id", sorted(DEFROST_CORE_IDS))
def test_defrost_explicit_individual_selection_still_works(point_id):
    assert point_enabled(PROFILE_INDIVIDUAL, point_id, [point_id])
    assert not point_enabled(PROFILE_INDIVIDUAL, point_id, [9659, 9663])


@pytest.mark.parametrize("point_id", [9659, 9663])
def test_tones_still_excluded_from_extended(point_id):
    assert not point_enabled(PROFILE_EXTENDED, point_id)
    assert point_enabled(PROFILE_COMPLETE, point_id)
