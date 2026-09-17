from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock

import pytest

from custom_components.nibe_local.api import NibeApiError, NibeLocalApi
from custom_components.nibe_local.entity import scaled_value
from custom_components.nibe_local.number import metadata_limits


def _point(
    variable_id: int,
    raw_value: int,
    *,
    divisor: int | float = 1,
    unit: str | None = None,
    short_unit: str | None = None,
) -> dict:
    metadata = {
        "variableId": variable_id,
        "divisor": divisor,
        "minValue": 0,
        "maxValue": 0,
    }
    if unit is not None:
        metadata["unit"] = unit
    if short_unit is not None:
        metadata["shortUnit"] = short_unit
    return {
        "metadata": metadata,
        "value": {
            "integerValue": raw_value,
            "stringValue": "",
            "isOk": True,
        },
    }


def test_firmware_metadata_overrides_fix_pv_scale_and_power_units() -> None:
    api = NibeLocalApi(object(), host="192.0.2.1", port=8443)
    api._language_checked = True
    api._request = AsyncMock(
        return_value={
            "29258": _point(29258, 17, divisor=1, unit="kW", short_unit="kW"),
            "25165": _point(25165, 3, unit="kWh", short_unit="kWh"),
            "25166": _point(25166, 4, unit="kWh", short_unit="kWh"),
        }
    )

    points = asyncio.run(api.get_points())

    assert points["29258"]["metadata"]["divisor"] == 100
    assert scaled_value(points["29258"]) == pytest.approx(0.17)
    assert points["25165"]["metadata"]["unit"] == "kW"
    assert points["25165"]["metadata"]["shortUnit"] == "kW"
    assert points["25166"]["metadata"]["unit"] == "kW"
    assert points["25166"]["metadata"]["shortUnit"] == "kW"


def test_single_point_fetch_applies_firmware_metadata_override() -> None:
    api = NibeLocalApi(object(), host="192.0.2.1", port=8443)
    api._request = AsyncMock(
        return_value=_point(29258, 17, divisor=1, unit="kW", short_unit="kW")
    )

    point = asyncio.run(api.get_point(29258))

    assert point["metadata"]["divisor"] == 100
    assert scaled_value(point) == pytest.approx(0.17)


def test_patch_rejection_in_http_200_body_raises_api_error() -> None:
    api = NibeLocalApi(object(), host="192.0.2.1", port=8443)
    api.get_point = AsyncMock(return_value=_point(123, 0))
    api._request = AsyncMock(return_value={"123": "error: read only value"})

    with pytest.raises(NibeApiError, match="read only value"):
        asyncio.run(api.patch_point(123, 1))


def test_patch_modified_response_is_accepted() -> None:
    api = NibeLocalApi(object(), host="192.0.2.1", port=8443)
    api.get_point = AsyncMock(return_value=_point(123, 0))
    api._request = AsyncMock(return_value={"123": "modified"})

    response = asyncio.run(api.patch_point(123, 1))

    assert response == {"123": "modified"}


def test_patch_full_point_object_with_is_ok_is_accepted() -> None:
    api = NibeLocalApi(object(), host="192.0.2.1", port=8443)
    api.get_point = AsyncMock(return_value=_point(123, 0))
    response = {"123": _point(123, 1)}
    api._request = AsyncMock(return_value=response)

    assert asyncio.run(api.patch_point(123, 1)) == response


def test_zero_zero_number_limits_are_untrusted_for_real_number_entities() -> None:
    point = _point(999, 0, divisor=1)

    assert metadata_limits(point, current=0.0, point_id=999) is None
    assert metadata_limits(point, current=5.0, point_id=999) is None


def test_explicit_safe_number_limits_still_win_over_zero_zero_metadata() -> None:
    point = _point(3702, 580, divisor=10)

    assert metadata_limits(point, current=58.0, point_id=3702) == (55.0, 70.0)
