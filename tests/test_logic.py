"""Regression tests for NIBE Local REST core logic."""

from datetime import time
import json
from pathlib import Path

from homeassistant.const import CONF_PASSWORD, CONF_USERNAME

from custom_components.nibe_local.api import NibeLocalApi
from custom_components.nibe_local.config_flow import merge_keep_credentials
from custom_components.nibe_local.const import (
    CONF_AUTH_HEADER,
    POINT_COOLING_ALLOWED,
    POINT_HEATING_ALLOWED,
    POINT_OPERATING_MODE_SETTING,
    POINT_VENTILATION_MODE,
)
from custom_components.nibe_local.coordinator import (
    CONNECTION_NOTIFICATION_DELAY_SECONDS,
    FALLBACK_BACKOFF_STEPS_SECONDS,
    auth_failure_notification_due,
    connection_failure_notification_due,
    fallback_backoff_delay,
    merge_point_updates,
    should_skip_fallback_scan,
)
from custom_components.nibe_local.entity import scaled_value, to_raw
from custom_components.nibe_local.number import metadata_limits, value_is_representable
from custom_components.nibe_local.select import (
    NibePointSelect,
    mapped_option,
    supports_smart_mode,
)
from custom_components.nibe_local.sensor import periodic_hot_water_date
from custom_components.nibe_local.switch import (
    write_allowed_after_mode_refresh,
    write_allowed_for_mode,
)
from custom_components.nibe_local.time import seconds_from_time, time_from_seconds

_TRANSLATIONS = (
    Path(__file__).parents[1] / "custom_components" / "nibe_local" / "translations"
)
_RUNTIME_EXCEPTION_KEYS = {
    "operating_mode_unavailable",
    "write_not_allowed_in_current_mode",
    "number_limits_unavailable",
    "number_out_of_range",
    "number_invalid_step",
    "auth_rejected",
    "auth_rejected_notification",
    "connection_unreachable_notification",
}


def _point(raw: int, *, divisor: int = 10, decimal: int = 1) -> dict:
    return {
        "metadata": {"divisor": divisor, "decimal": decimal},
        "value": {"integerValue": raw, "stringValue": ""},
    }


def test_scaled_value_and_to_raw_roundtrip() -> None:
    point = _point(222)
    assert scaled_value(point) == 22.2
    assert to_raw(point, 22.2) == 222


def test_normalize_points_accepts_single_point_and_wrappers() -> None:
    point = {
        "metadata": {"variableId": 4},
        "value": {"integerValue": 222, "stringValue": ""},
    }
    assert NibeLocalApi._normalize_points(point) == {"4": point}
    assert NibeLocalApi._normalize_points({"points": [point]}) == {"4": point}
    assert NibeLocalApi._normalize_points({"data": {"4": point}}) == {"4": point}


def test_normalize_points_accepts_mapping_without_variable_id() -> None:
    point = {"value": {"integerValue": 1, "stringValue": ""}}
    assert NibeLocalApi._normalize_points({"3920": point}) == {"3920": point}


def test_periodic_hot_water_date_epoch() -> None:
    assert periodic_hot_water_date(6093) == "07.09.2026"
    assert periodic_hot_water_date(6096) == "10.09.2026"
    assert periodic_hot_water_date(-1) is None
    assert periodic_hot_water_date("ungueltig") is None


def test_operating_mode_options_are_stable() -> None:
    assert NibePointSelect.ENUM_OPTIONS[POINT_OPERATING_MODE_SETTING] == {
        0: "auto",
        1: "manual",
        2: "auxiliary_heat_only",
    }


def test_ventilation_mode_options_are_stable() -> None:
    assert NibePointSelect.ENUM_OPTIONS[POINT_VENTILATION_MODE] == {
        0: "normal",
        1: "off",
        2: "reduced",
        3: "increased",
        4: "maximum",
    }


def test_mapped_option_accepts_integer_and_numeric_string() -> None:
    mapping = NibePointSelect.ENUM_OPTIONS[POINT_OPERATING_MODE_SETTING]
    assert mapped_option(0, mapping) == "auto"
    assert mapped_option("0", mapping) == "auto"
    assert mapped_option("2", mapping) == "auxiliary_heat_only"
    assert mapped_option("unbekannt", mapping) == "unbekannt"


def test_mode_dependent_write_protection() -> None:
    assert not write_allowed_for_mode(POINT_HEATING_ALLOWED, 0)
    assert not write_allowed_for_mode(POINT_COOLING_ALLOWED, 0)
    assert write_allowed_for_mode(POINT_HEATING_ALLOWED, 1)
    assert write_allowed_for_mode(POINT_COOLING_ALLOWED, 1)
    assert write_allowed_for_mode(POINT_HEATING_ALLOWED, 2)
    assert not write_allowed_for_mode(POINT_COOLING_ALLOWED, 2)
    assert not write_allowed_for_mode(POINT_HEATING_ALLOWED, None)


def test_protected_write_requires_successful_mode_refresh() -> None:
    assert write_allowed_after_mode_refresh(
        POINT_HEATING_ALLOWED, 1, refresh_succeeded=True
    )
    assert not write_allowed_after_mode_refresh(
        POINT_HEATING_ALLOWED, 1, refresh_succeeded=False
    )
    assert not write_allowed_after_mode_refresh(
        POINT_COOLING_ALLOWED, 1, refresh_succeeded=False
    )


def test_time_conversion_roundtrip() -> None:
    assert time_from_seconds(34200) == time(9, 30)
    assert seconds_from_time(time(9, 30)) == 34200
    assert time_from_seconds(0) == time(0, 0)
    assert time_from_seconds(86399) == time(23, 59, 59)
    assert time_from_seconds(-1) is None
    assert time_from_seconds(86400) is None
    assert time_from_seconds("ungueltig") is None


def test_metadata_limits_reject_ambiguous_zero_range() -> None:
    point = {
        "metadata": {
            "divisor": 10,
            "minValue": 0,
            "maxValue": 0,
        }
    }
    assert metadata_limits(point, 22.2) is None
    assert metadata_limits(point, 0) == (0.0, 0.0)


def test_metadata_limits_scale_values() -> None:
    point = {
        "metadata": {
            "divisor": 10,
            "minValue": 100,
            "maxValue": 500,
        }
    }
    assert metadata_limits(point, 20.0) == (10.0, 50.0)


def test_metadata_limits_reject_non_positive_divisor() -> None:
    zero = {"metadata": {"divisor": 0, "minValue": 0, "maxValue": 100}}
    negative = {"metadata": {"divisor": -10, "minValue": 0, "maxValue": 100}}
    assert metadata_limits(zero, 0) is None
    assert metadata_limits(negative, 0) is None
    assert not value_is_representable(zero, 1.0)
    assert not value_is_representable(negative, 1.0)


def test_number_value_must_match_nibe_step() -> None:
    point = {"metadata": {"divisor": 10, "minValue": 100, "maxValue": 500}}
    assert value_is_representable(point, 22.2)
    assert value_is_representable(point, 10.0)
    assert not value_is_representable(point, 22.25)


def test_fallback_backoff_delay_caps_at_120_seconds() -> None:
    assert FALLBACK_BACKOFF_STEPS_SECONDS == (30, 60, 120)
    assert fallback_backoff_delay(0) == 30
    assert fallback_backoff_delay(1) == 60
    assert fallback_backoff_delay(2) == 120
    assert fallback_backoff_delay(3) == 120
    assert fallback_backoff_delay(20) == 120
    assert fallback_backoff_delay(-1) == 30


def test_should_skip_fallback_scan_respects_window() -> None:
    assert should_skip_fallback_scan(now=100.0, next_attempt_at=110.0)
    assert not should_skip_fallback_scan(now=110.0, next_attempt_at=110.0)
    assert not should_skip_fallback_scan(now=120.0, next_attempt_at=110.0)


def test_fallback_backoff_never_skips_without_cached_points() -> None:
    assert not should_skip_fallback_scan(
        now=100.0,
        next_attempt_at=110.0,
        has_previous_points=False,
    )
    assert should_skip_fallback_scan(
        now=100.0,
        next_attempt_at=110.0,
        has_previous_points=True,
    )


def test_connection_notification_waits_two_minutes() -> None:
    assert CONNECTION_NOTIFICATION_DELAY_SECONDS == 120
    assert not connection_failure_notification_due(
        now=100.0, failure_started_at=None
    )
    assert not connection_failure_notification_due(
        now=219.9, failure_started_at=100.0
    )
    assert connection_failure_notification_due(
        now=220.0, failure_started_at=100.0
    )
    assert connection_failure_notification_due(
        now=300.0, failure_started_at=100.0
    )


def test_auth_notification_only_created_once_per_outage() -> None:
    assert auth_failure_notification_due(notification_active=False)
    assert not auth_failure_notification_due(notification_active=True)
    assert auth_failure_notification_due(notification_active=False)


def test_merge_point_updates_preserves_missing_old_values() -> None:
    previous = {"4": {"value": "old"}, "8": {"value": "keep"}}
    refreshed = {"4": {"value": "new"}, "10": {"value": "added"}}
    assert merge_point_updates(previous, refreshed) == {
        "4": {"value": "new"},
        "8": {"value": "keep"},
        "10": {"value": "added"},
    }


def test_merge_keep_credentials_preserves_masked_secrets() -> None:
    current = {
        CONF_USERNAME: "andi",
        CONF_PASSWORD: "old-password",
        CONF_AUTH_HEADER: "Basic old",
    }
    candidate = {
        CONF_USERNAME: "andi",
        CONF_PASSWORD: "",
        CONF_AUTH_HEADER: "",
    }
    merged = merge_keep_credentials(candidate, current)
    assert merged[CONF_PASSWORD] == "old-password"
    assert merged[CONF_AUTH_HEADER] == "Basic old"


def test_merge_keep_credentials_treats_whitespace_only_as_blank() -> None:
    current = {
        CONF_USERNAME: "andi",
        CONF_PASSWORD: "old-password",
        CONF_AUTH_HEADER: "Basic old",
    }
    candidate = {
        CONF_USERNAME: "andi",
        CONF_PASSWORD: "   ",
        CONF_AUTH_HEADER: "\t  ",
    }
    merged = merge_keep_credentials(candidate, current)
    assert merged[CONF_PASSWORD] == "old-password"
    assert merged[CONF_AUTH_HEADER] == "Basic old"


def test_merge_keep_credentials_preserves_non_blank_whitespace() -> None:
    current = {
        CONF_USERNAME: "andi",
        CONF_PASSWORD: "old-password",
        CONF_AUTH_HEADER: "Basic old",
    }
    candidate = {
        CONF_USERNAME: "andi",
        CONF_PASSWORD: " new-password ",
        CONF_AUTH_HEADER: " Basic new ",
    }
    merged = merge_keep_credentials(candidate, current)
    assert merged[CONF_PASSWORD] == " new-password "
    assert merged[CONF_AUTH_HEADER] == " Basic new "


def test_merge_keep_credentials_replaces_provided_secrets() -> None:
    current = {
        CONF_USERNAME: "andi",
        CONF_PASSWORD: "old-password",
        CONF_AUTH_HEADER: "Basic old",
    }
    candidate = {
        CONF_USERNAME: "andi",
        CONF_PASSWORD: "new-password",
        CONF_AUTH_HEADER: "Basic new",
    }
    merged = merge_keep_credentials(candidate, current)
    assert merged[CONF_PASSWORD] == "new-password"
    assert merged[CONF_AUTH_HEADER] == "Basic new"


def test_supports_smart_mode_only_when_device_exposes_key() -> None:
    assert supports_smart_mode({"smartMode": "normal"})
    assert supports_smart_mode({"smartMode": None})
    assert not supports_smart_mode({})
    assert not supports_smart_mode(None)


def test_runtime_translations_are_complete_in_de_and_en() -> None:
    for language in ("de", "en"):
        payload = json.loads((_TRANSLATIONS / f"{language}.json").read_text())
        assert payload["entity"]["switch"]["ventilation_plus"]["name"]
        assert _RUNTIME_EXCEPTION_KEYS <= set(payload["exceptions"])
        for key in _RUNTIME_EXCEPTION_KEYS:
            assert payload["exceptions"][key]["message"]
