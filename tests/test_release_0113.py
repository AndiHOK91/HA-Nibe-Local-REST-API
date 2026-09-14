"""Release-specific regressions for v0.11.3."""

from base64 import b64encode
import json
from pathlib import Path

from custom_components.nibe_local.api import NibeLocalApi
from custom_components.nibe_local.const import (
    AUTH_METHOD_BASIC,
    POINTS,
)
from custom_components.nibe_local.number import metadata_limits

_TRANSLATIONS = (
    Path(__file__).parents[1] / "custom_components" / "nibe_local" / "translations"
)


def test_periodic_hot_water_stop_uses_safe_limits_despite_bad_rest_metadata() -> None:
    point = {
        "metadata": {
            "divisor": 10,
            "minValue": 55,
            "maxValue": 700,
        }
    }

    assert metadata_limits(point, 58.0, 3702) == (55.0, 70.0)


def test_basic_auth_is_encoded_as_header_without_aiohttp_basicauth() -> None:
    api = NibeLocalApi(
        object(),
        host="192.0.2.1",
        port=8443,
        username="andi",
        password="secret",
        auth_method=AUTH_METHOD_BASIC,
    )
    expected = b64encode(b"andi:secret").decode("ascii")
    assert api._headers()["Authorization"] == f"Basic {expected}"


def test_every_curated_point_has_german_and_english_entity_text() -> None:
    for language in ("de", "en"):
        payload = json.loads((_TRANSLATIONS / f"{language}.json").read_text(encoding="utf-8"))
        entities = payload["entity"]
        missing = [
            f"{definition.platform}.{definition.key}"
            for definition in POINTS
            if definition.key not in entities.get(definition.platform, {})
        ]
        assert not missing, f"Missing {language} translations: {missing}"


def test_obsolete_alternative_gp1_translation_key_is_removed() -> None:
    for language in ("de", "en"):
        payload = json.loads((_TRANSLATIONS / f"{language}.json").read_text(encoding="utf-8"))
        assert "heating_circulation_pump_gp1_2792" not in payload["entity"]["sensor"]
