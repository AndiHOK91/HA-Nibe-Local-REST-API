"""Platform import smoke tests."""

import importlib

from custom_components.nibe_local.const import DOMAIN, PLATFORMS


def test_all_platform_modules_import_and_expose_setup() -> None:
    """Every declared platform must import and expose async_setup_entry."""
    for platform in PLATFORMS:
        module = importlib.import_module(f"custom_components.{DOMAIN}.{platform}")
        assert callable(getattr(module, "async_setup_entry", None)), platform
