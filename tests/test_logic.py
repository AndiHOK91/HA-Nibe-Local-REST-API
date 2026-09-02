"""Regression tests for NIBE Local REST core logic."""

import asyncio
from datetime import time
import json
from pathlib import Path

from homeassistant.const import CONF_PASSWORD, CONF_USERNAME

from custom_components.nibe_local.alarms import normalize_alarm
from custom_components.nibe_local.api import NibeLocalApi
from custom_components.nibe_local.config_flow import (
    _connection_schema,
    _reauth_schema,
    auth_method_from_values,
    merge_auth_settings,
)
from custom_components.nibe_local.const import (
    AUTH_METHOD_BASIC,
    AUTH_METHOD_HEADER,
    CONF_AUTH_HEADER,
    CONF_AUTH_METHOD,
    NIBE_DEVICE_ID,
    POINTS,
    POINT_COOLING_ALLOWED,
    POINT_HEATING_ALLOWED,
    POINT_HOT_WATER_DEMAND,
    POINT_OPERATING_MODE_SETTING,
    POINT_VENTILATION_MODE,
)
from custom_components.nibe_local.coordinator import (
    CONNECTION_NOTIFICATION_DELAY_SECONDS,
    FALLBACK_BACKOFF_STEPS_SECONDS,
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
from custom_components.nibe_local.sensor import (
    is_relative_humidity,
    normalize_unit,
    periodic_hot_water_date,
)
from custom_components.nibe_local.switch import write_allowed_for_mode
from custom_components.nibe_local.time import seconds_from_time, time_from_seconds
from custom_components.nibe_local import binary_sensor, number, select, sensor, switch, time as time_platform

_TRANSLATIONS = (
    Path(__file__).parents[1] / "custom_components" / "nibe_local" / "translations"
)
_RUNTIME_EXCEPTION_KEYS = {
    "operating_mode_unavailable",
    "write_not_allowed_in_current_mode",
    "number_limits_unavailable",
    "number_out_of_range",
    "number_invalid_step",
    "select_invalid_option",
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


def test_alarm_prefers_device_language_text() -> None:
    alarm = normalize_alarm(
        {
            "alarmId": 224,
            "header": "Device supplied alarm text",
        }
    )
    assert alarm["text"] == "Device supplied alarm text"


def test_alarm_uses_verified_german_fallback_when_device_text_is_missing() -> None:
    alarm = normalize_alarm({"alarmId": 224}, "de")
    assert alarm["text"] == "Kom.fehler mit Zubehör Brauchwasserkomfort"


def test_alarm_does_not_use_german_fallback_for_other_languages() -> None:
    assert normalize_alarm({"alarmId": 224}, "en")["text"] == "Alarm 224"
    assert normalize_alarm({"alarmId": 224}, None)["text"] == "Alarm 224"


def test_unknown_alarm_fallback_is_language_neutral() -> None:
    assert normalize_alarm({"alarmId": 99999})["text"] == "Alarm 99999"
    assert normalize_alarm({})["text"] == "Alarm"


def test_nibe_units_are_normalized_for_home_assistant() -> None:
    assert normalize_unit("%RH") == "%"
    assert normalize_unit("l/min") == "L/min"
    assert normalize_unit("°C") == "°C"
    assert normalize_unit(None) is None


def test_only_explicit_nibe_relative_humidity_unit_is_humidity() -> None:
    assert is_relative_humidity({"metadata": {"unit": "%RH", "shortUnit": "%"}})
    assert not is_relative_humidity({"metadata": {"unit": "%", "shortUnit": "%"}})


def test_device_id_is_fixed() -> None:
    assert NIBE_DEVICE_ID == "0"


def test_parallel_update_limits_are_explicit() -> None:
    assert sensor.PARALLEL_UPDATES == 0
    assert binary_sensor.PARALLEL_UPDATES == 0
    assert switch.PARALLEL_UPDATES == 1
    assert number.PARALLEL_UPDATES == 1
    assert select.PARALLEL_UPDATES == 1
    assert time_platform.PARALLEL_UPDATES == 1


def test_api_write_requests_are_serialized() -> None:
    async def run_test() -> None:
        api = NibeLocalApi(
            object(),
            host="192.0.2.1",
            port=8443,
        )
        active = 0
        maximum_active = 0

        async def fake_request(method: str, path: str, *, json=None):
            nonlocal active, maximum_active
            active += 1
            maximum_active = max(maximum_active, active)
            await asyncio.sleep(0)
            active -= 1
            return None

        api._request = fake_request
        await asyncio.gather(
            api.patch_point(3920, 1),
            api.set_smart_mode("away"),
        )
        assert maximum_active == 1

    asyncio.run(run_test())


def test_all_point_selects_have_explicit_enum_mappings() -> None:
    configured = {
        definition.point_id for definition in POINTS if definition.platform == "select"
    }
    assert configured == set(NibePointSelect.ENUM_OPTIONS)


def test_point_groups_use_stable_language_neutral_keys() -> None:
    expected_groups = {
        "system",
        "heating",
        "cooling",
        "hot_water",
        "energy",
        "hydraulics",
        "heat_pump",
        "eev_defrost",
        "ventilation",
    }
    assert {definition.group for definition in POINTS} == expected_groups


def test_operating_mode_options_are_stable() -> None:
    assert NibePointSelect.ENUM_OPTIONS[POINT_OPERATING_MODE_SETTING] == {
        0: "auto",
        1: "manual",
        2: "auxiliary_heat_only",
    }


def test_hot_water_demand_options_are_stable() -> None:
    assert NibePointSelect.ENUM_OPTIONS[POINT_HOT_WATER_DEMAND] == {
        0: "low",
        1: "medium",
        2: "high",
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


def test_merge_point_updates_preserves_missing_old_values() -> None:
    previous = {"4": {"value": "old"}, "8": {"value": "keep"}}
    refreshed = {"4": {"value": "new"}, "10": {"value": "added"}}
    assert merge_point_updates(previous, refreshed) == {
        "4": {"value": "new"},
        "8": {"value": "keep"},
        "10": {"value": "added"},
    }


def test_auth_method_is_inferred_for_existing_entries() -> None:
    assert auth_method_from_values({CONF_AUTH_HEADER: "Basic old"}) == AUTH_METHOD_HEADER
    assert auth_method_from_values({CONF_AUTH_HEADER: ""}) == AUTH_METHOD_BASIC
    assert auth_method_from_values({}) == AUTH_METHOD_BASIC


def test_explicit_auth_method_wins_over_legacy_values() -> None:
    values = {
        CONF_AUTH_METHOD: AUTH_METHOD_BASIC,
        CONF_AUTH_HEADER: "Basic old",
    }
    assert auth_method_from_values(values) == AUTH_METHOD_BASIC


def test_api_uses_only_the_explicit_authentication_method() -> None:
    basic = NibeLocalApi(
        object(),
        host="192.0.2.1",
        port=8443,
        username="andi",
        password="secret",
        auth_header="Basic stale",
        auth_method=AUTH_METHOD_BASIC,
    )
    assert basic._auth is not None
    assert basic._auth.login == "andi"
    assert basic._auth_header is None

    header = NibeLocalApi(
        object(),
        host="192.0.2.1",
        port=8443,
        username="stale-user",
        password="stale-password",
        auth_header="Basic current",
        auth_method=AUTH_METHOD_HEADER,
    )
    assert header._auth is None
    assert header._auth_header == "Basic current"


def test_api_keeps_legacy_header_precedence_without_auth_method() -> None:
    legacy = NibeLocalApi(
        object(),
        host="192.0.2.1",
        port=8443,
        username="andi",
        password="secret",
        auth_header="Basic legacy",
    )
    assert legacy._headers()["Authorization"] == "Basic legacy"


def _schema_keys(schema) -> set[str]:
    """Return plain key names from a voluptuous schema."""
    return {
        str(key.schema if hasattr(key, "schema") else key)
        for key in schema.schema
    }


def test_connection_schema_has_fixed_device_id_and_auth_method() -> None:
    keys = _schema_keys(_connection_schema({}))
    assert "device_id" not in keys
    assert CONF_AUTH_METHOD in keys


def test_reauth_schema_only_shows_active_authentication_method() -> None:
    basic_keys = _schema_keys(
        _reauth_schema(
            {
                CONF_AUTH_METHOD: AUTH_METHOD_BASIC,
                CONF_USERNAME: "andi",
                CONF_PASSWORD: "secret",
            }
        )
    )
    assert CONF_USERNAME in basic_keys
    assert CONF_PASSWORD in basic_keys
    assert CONF_AUTH_HEADER not in basic_keys

    header_keys = _schema_keys(
        _reauth_schema(
            {
                CONF_AUTH_METHOD: AUTH_METHOD_HEADER,
                CONF_AUTH_HEADER: "Basic abc",
            }
        )
    )
    assert CONF_AUTH_HEADER in header_keys
    assert CONF_USERNAME not in header_keys
    assert CONF_PASSWORD not in header_keys


def test_switching_to_basic_does_not_revive_an_inactive_password() -> None:
    current = {
        CONF_AUTH_METHOD: AUTH_METHOD_HEADER,
        CONF_USERNAME: "andi",
        CONF_PASSWORD: "old-password",
        CONF_AUTH_HEADER: "Basic old",
    }
    candidate = {
        CONF_AUTH_METHOD: AUTH_METHOD_BASIC,
        CONF_USERNAME: "andi",
        CONF_PASSWORD: "",
    }
    merged = merge_auth_settings(candidate, current)
    assert merged[CONF_AUTH_METHOD] == AUTH_METHOD_BASIC
    assert merged[CONF_PASSWORD] == ""
    assert merged[CONF_AUTH_HEADER] == ""


def test_basic_auth_preserves_blank_password_when_method_is_unchanged() -> None:
    current = {
        CONF_AUTH_METHOD: AUTH_METHOD_BASIC,
        CONF_USERNAME: "andi",
        CONF_PASSWORD: "old-password",
        CONF_AUTH_HEADER: "",
    }
    candidate = {
        CONF_AUTH_METHOD: AUTH_METHOD_BASIC,
        CONF_USERNAME: "andi",
        CONF_PASSWORD: " ",
    }
    merged = merge_auth_settings(candidate, current)
    assert merged[CONF_PASSWORD] == "old-password"
    assert merged[CONF_AUTH_HEADER] == ""


def test_header_auth_preserves_blank_header_and_clears_basic_credentials() -> None:
    current = {
        CONF_AUTH_METHOD: AUTH_METHOD_HEADER,
        CONF_USERNAME: "andi",
        CONF_PASSWORD: "old-password",
        CONF_AUTH_HEADER: "Basic old",
    }
    candidate = {
        CONF_AUTH_METHOD: AUTH_METHOD_HEADER,
        CONF_AUTH_HEADER: "\t  ",
    }
    merged = merge_auth_settings(candidate, current)
    assert merged[CONF_AUTH_METHOD] == AUTH_METHOD_HEADER
    assert merged[CONF_AUTH_HEADER] == "Basic old"
    assert merged[CONF_USERNAME] == ""
    assert merged[CONF_PASSWORD] == ""


def test_switching_to_header_replaces_header_and_removes_basic_auth() -> None:
    current = {
        CONF_AUTH_METHOD: AUTH_METHOD_BASIC,
        CONF_USERNAME: "andi",
        CONF_PASSWORD: "old-password",
        CONF_AUTH_HEADER: "",
    }
    candidate = {
        CONF_AUTH_METHOD: AUTH_METHOD_HEADER,
        CONF_AUTH_HEADER: " Basic new ",
    }
    merged = merge_auth_settings(candidate, current)
    assert merged[CONF_AUTH_HEADER] == " Basic new "
    assert merged[CONF_USERNAME] == ""
    assert merged[CONF_PASSWORD] == ""


def test_switching_to_header_does_not_revive_an_inactive_header() -> None:
    current = {
        CONF_AUTH_METHOD: AUTH_METHOD_BASIC,
        CONF_USERNAME: "andi",
        CONF_PASSWORD: "old-password",
        CONF_AUTH_HEADER: "Basic stale",
    }
    candidate = {
        CONF_AUTH_METHOD: AUTH_METHOD_HEADER,
        CONF_AUTH_HEADER: "",
    }
    merged = merge_auth_settings(candidate, current)
    assert merged[CONF_AUTH_HEADER] == ""
    assert merged[CONF_USERNAME] == ""
    assert merged[CONF_PASSWORD] == ""


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
