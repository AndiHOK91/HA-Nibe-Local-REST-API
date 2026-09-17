"""Regression tests for Local REST titles and service selector metadata."""

from pathlib import Path

import yaml

from custom_components.nibe_local import (
    ATTR_CONFIG_ENTRY_ID,
    ATTR_HISTORY_DAYS,
    SERVICE_EXPORT_EXTENDED_DIAGNOSTICS_SCHEMA,
)
from custom_components.nibe_local.entity import local_api_point_name


def test_local_api_point_name_prefers_title() -> None:
    point = {
        "title": "Außen-Flüss.leit.-Fühler (EB101-BT39)",
        "description": "Fallback description",
        "metadata": {},
    }

    assert local_api_point_name(point) == "Außen-Flüss.leit.-Fühler (EB101-BT39)"


def test_local_api_point_name_supports_metadata_title() -> None:
    point = {"metadata": {"title": "Metadata title"}}

    assert local_api_point_name(point) == "Metadata title"


def test_local_api_point_name_keeps_description_fallback() -> None:
    point = {"description": "Current outdoor temperature (BT1)", "metadata": {}}

    assert local_api_point_name(point) == "Current outdoor temperature (BT1)"


def test_extended_diagnostics_schema_accepts_selector_strings() -> None:
    validated = SERVICE_EXPORT_EXTENDED_DIAGNOSTICS_SCHEMA(
        {
            ATTR_CONFIG_ENTRY_ID: "test-entry",
            ATTR_HISTORY_DAYS: "3",
        }
    )

    assert validated[ATTR_HISTORY_DAYS] == 3


def test_services_yaml_select_values_are_strings() -> None:
    services_path = (
        Path(__file__).parents[1]
        / "custom_components"
        / "nibe_local"
        / "services.yaml"
    )
    services = yaml.safe_load(services_path.read_text(encoding="utf-8"))
    history = services["export_extended_diagnostics"]["fields"]["history_days"]

    assert history["default"] == "1"
    assert [option["value"] for option in history["selector"]["select"]["options"]] == [
        "1",
        "3",
        "5",
        "7",
    ]
