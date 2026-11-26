"""Keep hot-water circulation runtime names precise and entity IDs stable."""
import json
from pathlib import Path

import pytest

from custom_components.nibe_local.const import POINTS


@pytest.mark.parametrize(
    "point_id,key,german,english",
    [
        (3710, "hot_water_operating_time", "Brauchwasserzirkulation Betriebszeit",
         "Hot water circulation operating time"),
        (3711, "hot_water_standstill_time", "Brauchwasserzirkulation Stillstandszeit",
         "Hot water circulation standstill time"),
    ],
)
def test_hot_water_circulation_times_are_number_entities_with_translated_names(
    point_id, key, german, english
):
    definition = next(point for point in POINTS if point.point_id == point_id)
    assert definition.platform == "number"
    assert definition.key == key
    base = Path(__file__).resolve().parents[1] / "custom_components" / "nibe_local" / "translations"
    for language, expected in (("de", german), ("en", english)):
        data = json.loads((base / f"{language}.json").read_text(encoding="utf-8"))
        assert data["entity"]["number"][key]["name"] == expected
