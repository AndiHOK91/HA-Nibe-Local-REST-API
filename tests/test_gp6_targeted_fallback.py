"""Regression tests for GP6 targeted point supplementation."""

import asyncio
from unittest.mock import AsyncMock

from custom_components.nibe_local.api import (
    NibeApiError,
    NibeLocalApi,
    TARGETED_POINT_FALLBACK_IDS,
)


def _point(variable_id: int, value: int) -> dict:
    return {
        "metadata": {"variableId": variable_id},
        "value": {"integerValue": value, "stringValue": ""},
    }


def test_gp6_is_configured_for_targeted_fallback() -> None:
    assert TARGETED_POINT_FALLBACK_IDS == (10895,)


def test_get_points_supplements_gp6_when_bulk_omits_it() -> None:
    async def run() -> None:
        api = NibeLocalApi(None, "nibe.local", 8443)
        api._request = AsyncMock(
            side_effect=[
                {"points": [_point(4, 222)]},
                _point(10895, 1),
            ]
        )

        points = await api.get_points()

        assert set(points) == {"4", "10895"}
        assert points["10895"]["value"]["integerValue"] == 1
        assert api._request.await_count == 2
        api._request.assert_any_await("GET", "/devices/0/points/10895")

    asyncio.run(run())


def test_get_points_does_not_refetch_gp6_when_bulk_contains_it() -> None:
    async def run() -> None:
        api = NibeLocalApi(None, "nibe.local", 8443)
        api._request = AsyncMock(
            return_value={"points": [_point(4, 222), _point(10895, 0)]}
        )

        points = await api.get_points()

        assert points["10895"]["value"]["integerValue"] == 0
        assert api._request.await_count == 1

    asyncio.run(run())


def test_optional_gp6_read_failure_keeps_bulk_points() -> None:
    async def run() -> None:
        api = NibeLocalApi(None, "nibe.local", 8443)
        api._request = AsyncMock(
            side_effect=[
                {"points": [_point(4, 222)]},
                NibeApiError("HTTP 404: Not Found"),
            ]
        )

        points = await api.get_points()

        assert set(points) == {"4"}
        assert api._request.await_count == 2

    asyncio.run(run())
