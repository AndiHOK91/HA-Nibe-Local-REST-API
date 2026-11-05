"""Whole-degree steps for NIBE design outdoor temperature (3868)."""
import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from homeassistant.exceptions import HomeAssistantError
from custom_components.nibe_local.number import NibeDiscoveredNumber


def entity():
    e = object.__new__(NibeDiscoveredNumber)
    e.point_id = 3868
    p = {'metadata': {'divisor': 10, 'minValue': -400, 'maxValue': 200},
         'value': {'integerValue': -100}}
    e.coordinator = SimpleNamespace(point=lambda pid: p,
        api=SimpleNamespace(patch_point=AsyncMock()), async_refresh_point=AsyncMock())
    return e


def test_whole_degree_step_and_scaled_range():
    e = entity()
    assert e.native_step == 1
    assert (e.native_min_value, e.native_max_value) == (-40, 20)
    assert e.native_value == -10


@pytest.mark.parametrize('value', [-40, -11, -9, 0, 20])
def test_whole_degrees_write_scaled_raw_value(value):
    e = entity()
    asyncio.run(e.async_set_native_value(value))
    e.coordinator.api.patch_point.assert_awaited_once_with(3868, value * 10)


@pytest.mark.parametrize('value', [-40.1, -10.5, -0.1, 19.5, 20.1])
def test_fractional_or_out_of_range_values_do_not_reach_device(value):
    e = entity()
    with pytest.raises(HomeAssistantError):
        asyncio.run(e.async_set_native_value(value))
    e.coordinator.api.patch_point.assert_not_awaited()
