"""Regression tests for redundant NIBE REST write protection."""

import inspect

from custom_components.nibe_local.api import NibeLocalApi


def _point(integer=None, string=""):
    return {
        "value": {
            "integerValue": integer,
            "stringValue": string,
        }
    }


def test_point_raw_value_prefers_non_empty_string_value() -> None:
    assert NibeLocalApi._point_raw_value(_point(0, "manual")) == "manual"
    assert NibeLocalApi._point_raw_value(_point(1, "")) == 1
    assert NibeLocalApi._point_raw_value({}) is None


def test_patch_point_reads_before_writing_and_skips_identical_value() -> None:
    source = inspect.getsource(NibeLocalApi.patch_point)

    assert "async with self._write_lock" in source
    assert "current_point = await self.get_point(variable_id)" in source
    assert "self._point_raw_value(current_point) == normalized_value" in source
    assert "return None" in source
    assert '"PATCH"' in source


def test_patch_point_keeps_write_fallback_when_pre_read_fails() -> None:
    source = inspect.getsource(NibeLocalApi.patch_point)

    assert "except NibeApiError" in source
    assert "proceeding with PATCH" in source
