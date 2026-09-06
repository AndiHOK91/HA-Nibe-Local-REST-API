"""Regression tests for NIBE defrost status values."""

import json
from pathlib import Path

from custom_components.nibe_local.const import POINTS, POINT_TIME_TO_DEFROST
from custom_components.nibe_local.sensor import description_enum_map


REST_LAST_DEFROST_DESCRIPTION_EN = (
    "0 = Successful, 1: Low supply, 2: Low return, "
    "3: Low flow, 4: Low LP, 5: Max time, 255 = Not accessible"
)


def test_time_to_defrost_is_diagnostic() -> None:
    definition = next(point for point in POINTS if point.point_id == POINT_TIME_TO_DEFROST)
    assert definition.diagnostic is True


def test_current_status_is_diagnostic_only() -> None:
    definition = next(point for point in POINTS if point.point_id == 2022)
    assert definition.diagnostic is True


def test_last_defrost_enum_is_parsed_only_from_rest_description() -> None:
    point = {"description": REST_LAST_DEFROST_DESCRIPTION_EN}
    assert description_enum_map(point) == {
        0: "Successful",
        1: "Low supply",
        2: "Low return",
        3: "Low flow",
        4: "Low LP",
        5: "Max time",
        255: "Not accessible",
    }


def test_last_defrost_without_rest_description_has_no_assumed_mapping() -> None:
    assert description_enum_map({}) == {}


def _translation(language: str) -> dict:
    path = Path("custom_components/nibe_local/translations") / f"{language}.json"
    return json.loads(path.read_text(encoding="utf-8"))


def test_last_defrost_german_state_translations_cover_rest_values() -> None:
    states = _translation("de")["entity"]["sensor"]["last_defrost_heat_pump_1"]["state"]
    assert states["Successful"] == "Erfolgreich"
    assert states["Low supply"] == "Vorlauftemperatur zu niedrig"
    assert states["Low return"] == "Rücklauftemperatur zu niedrig"
    assert states["Low flow"] == "Volumenstrom zu niedrig"
    assert states["Low LP"] == "Niederdruck zu niedrig"
    assert states["Max time"] == "Maximale Abtauzeit erreicht"
    assert states["Not accessible"] == "Nicht verfügbar"


def test_last_defrost_english_state_translations_cover_rest_values() -> None:
    states = _translation("en")["entity"]["sensor"]["last_defrost_heat_pump_1"]["state"]
    assert states["Successful"] == "Successful"
    assert states["Low supply"] == "Supply temperature too low"
    assert states["Low return"] == "Return temperature too low"
    assert states["Low flow"] == "Flow rate too low"
    assert states["Low LP"] == "Low pressure too low"
    assert states["Max time"] == "Maximum defrost time reached"
    assert states["Not accessible"] == "Not available"
