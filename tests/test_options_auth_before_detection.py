"""Regression tests for authenticated equipment detection in options flow."""

import inspect

from custom_components.nibe_local.config_flow import NibeLocalOptionsFlow


def test_options_init_does_not_discover_equipment() -> None:
    """Opening options must never use possibly stale stored credentials."""
    source = inspect.getsource(NibeLocalOptionsFlow.async_step_init)
    assert "_validate_and_discover" not in source
    assert "detect_equipment" not in source
    assert "async_step_auth_basic" in source
    assert "async_step_auth_header" in source


def test_options_authentication_precedes_equipment_ui() -> None:
    """Equipment UI is reached only after authenticated device/point discovery."""
    source = inspect.getsource(NibeLocalOptionsFlow._async_finish_auth)
    discovery = source.index("_validate_and_discover")
    detection = source.index("detect_equipment")
    return_to_options = source.index("async_step_init")
    assert discovery < detection < return_to_options


def test_failed_auth_cannot_update_detection_baseline() -> None:
    """Detection baseline is persisted only after successful discovery and user review."""
    auth_source = inspect.getsource(NibeLocalOptionsFlow._async_finish_auth)
    before_success = auth_source.split("else:", 1)[0]
    assert "CONF_DETECTED_EQUIPMENT" not in before_success

    init_source = inspect.getsource(NibeLocalOptionsFlow.async_step_init)
    assert "CONF_DETECTED_EQUIPMENT" in init_source
    assert "_authenticated_options_ready" in init_source
