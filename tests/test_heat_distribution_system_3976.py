"""Regression tests for NIBE heat distribution system point 3976."""

import json
from pathlib import Path

from custom_components.nibe_local.const import POINTS, POINT_HEAT_DISTRIBUTION_SYSTEM
from custom_components.nibe_local.select import NibePointSelect


def test_point_3976_is_curated_heat_distribution_select():
    definition = next(
        point for point in POINTS if point.point_id == POINT_HEAT_DISTRIBUTION_SYSTEM
    )
    assert definition.key == "heat_distribution_system"
    assert definition.group == "heating"
    assert definition.platform == "select"


def test_point_3976_firmware_enum_mapping():
    assert NibePointSelect.ENUM_OPTIONS[POINT_HEAT_DISTRIBUTION_SYSTEM] == {
        0: "own_setting",
        1: "radiator",
        2: "underfloor_heating",
        3: "radiator_and_underfloor_heating",
    }


def test_point_3976_translations_use_heat_distribution_name():
    root = Path(__file__).parents[1] / "custom_components" / "nibe_local" / "translations"
    de = json.loads((root / "de.json").read_text(encoding="utf-8"))
    en = json.loads((root / "en.json").read_text(encoding="utf-8"))

    de_entry = de["entity"]["select"]["heat_distribution_system"]
    en_entry = en["entity"]["select"]["heat_distribution_system"]

    assert de_entry["name"] == "Wärmeverteilsystem"
    assert "Luftvolumenstrom" not in de_entry["name"]
    assert de_entry["state"] == {
        "own_setting": "Eigene Einstellung",
        "radiator": "Heizkörper",
        "underfloor_heating": "Fußbodenheizung",
        "radiator_and_underfloor_heating": "Heizkörper + Fußbodenheizung",
    }
    assert en_entry["name"] == "Heat distribution system"
