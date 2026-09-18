"""Regression tests for Local REST titles and service selector metadata."""

from pathlib import Path

import yaml

from custom_components.nibe_local import (
    ATTR_CONFIG_ENTRY_ID,
    ATTR_HISTORY_DAYS,
    SERVICE_EXPORT_EXTENDED_DIAGNOSTICS_SCHEMA,
)
from custom_components.nibe_local.api import NibeLocalApi
from custom_components.nibe_local.config_flow import _point_label
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


def test_config_flow_point_label_uses_rest_title() -> None:
    point = {
        "title": "Außen-Flüss.leit.-Fühler (EB101-BT39)",
        "metadata": {"shortUnit": "°C"},
    }

    assert _point_label("28034", point) == (
        "Außen-Flüss.leit.-Fühler (EB101-BT39) · Variable ID 28034 [°C]"
    )


def test_config_flow_point_label_uses_metadata_title() -> None:
    point = {"metadata": {"title": "Metadata title"}}

    assert _point_label("999999", point) == "Metadata title · Variable ID 999999"


def test_nibe_language_point_sets_accept_language_header() -> None:
    api = NibeLocalApi(object(), host="192.0.2.1", port=8443)

    api._update_language_from_point({"value": {"integerValue": 2}})

    assert api._headers()["Accept-Language"] == "de"


def test_unknown_nibe_language_does_not_force_a_locale() -> None:
    api = NibeLocalApi(object(), host="192.0.2.1", port=8443)

    api._update_language_from_point({"value": {"integerValue": 25}})

    assert "Accept-Language" not in api._headers()


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
