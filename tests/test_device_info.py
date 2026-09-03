"""Tests for NIBE device metadata normalization."""

from types import SimpleNamespace

from custom_components.nibe_local.entity import (
    coordinator_device_info,
    device_product_details,
)


def test_device_product_details_support_nested_nibe_product_fields() -> None:
    """Model, software and serial should be detected from nested product data."""
    device = {
        "product": {
            "productName": "NIBE VVM S320 E EM 3x400V",
            "softwareVersion": "4.12.8",
            "serialNumber": "PRIVATE-SERIAL",
            "manufacturer": "NIBE",
        }
    }

    details = device_product_details(device)

    assert details == {
        "manufacturer": "NIBE",
        "name": "NIBE VVM S320 E EM 3x400V",
        "software_version": "4.12.8",
        "serial_number": "PRIVATE-SERIAL",
    }


def test_device_product_details_keep_legacy_fields() -> None:
    """Existing name/firmwareId payloads must remain supported."""
    details = device_product_details(
        {
            "product": {
                "name": "VVM S320",
                "firmwareId": "4.4.7",
                "serialNumber": "123",
            }
        }
    )

    assert details["name"] == "VVM S320"
    assert details["software_version"] == "4.4.7"
    assert details["serial_number"] == "123"


def test_coordinator_device_info_exposes_model_and_software_version() -> None:
    """Home Assistant device info should show normalized product information."""
    coordinator = SimpleNamespace(
        data={
            "device": {
                "product": {
                    "productName": "NIBE VVM S320 E EM 3x400V",
                    "softwareVersion": "4.12.8",
                    "serialNumber": "PRIVATE-SERIAL",
                }
            }
        },
        api=SimpleNamespace(device_id=0),
    )

    info = coordinator_device_info(coordinator)

    assert info["manufacturer"] == "NIBE"
    assert info["name"] == "NIBE VVM S320 E EM 3x400V"
    assert info["model"] == "NIBE VVM S320 E EM 3x400V"
    assert info["sw_version"] == "4.12.8"
