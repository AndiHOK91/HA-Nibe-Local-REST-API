"""Regression tests for read-only NIBE time values."""

import inspect
from datetime import time

from custom_components.nibe_local.time import (
    NibeTime,
    TIME_WRITE_LIMITATION,
    time_from_seconds,
)


def test_nibe_time_decodes_seconds_since_midnight() -> None:
    assert time_from_seconds(0) == time(0, 0)
    assert time_from_seconds(34200) == time(9, 30)
    assert time_from_seconds(43200) == time(12, 0)
    assert time_from_seconds(86399) == time(23, 59, 59)
    assert time_from_seconds(86400) is None


def test_time_write_limitation_is_documented_as_nibe_api_limitation() -> None:
    source = inspect.getsource(__import__("custom_components.nibe_local.time", fromlist=["*"]))
    assert 'points 3708 and 7849' in source
    assert 'HTTP 400' in source
    assert 'firmware / public-local-API limitation' in source
    assert 'not a seconds-since-midnight conversion error' in source


def test_time_set_value_is_blocked_before_any_rest_write() -> None:
    source = inspect.getsource(NibeTime.async_set_value)
    assert 'raise HomeAssistantError(TIME_WRITE_LIMITATION)' in source
    assert 'patch_point' not in source
    assert 'async_refresh_point' not in source
    assert 'firmware/API limitation' in TIME_WRITE_LIMITATION
