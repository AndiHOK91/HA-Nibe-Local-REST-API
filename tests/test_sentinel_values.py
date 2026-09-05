"""Regression tests for invalid integer limit sentinels."""

from custom_components.nibe_local.entity import raw_value_is_sentinel, scaled_value


def _point(raw: int, variable_size: str, *, minimum=0, maximum=0, divisor=1):
    return {
        "value": {"integerValue": raw, "stringValue": "", "isOk": True},
        "metadata": {
            "variableSize": variable_size,
            "minValue": minimum,
            "maxValue": maximum,
            "divisor": divisor,
            "decimal": 1 if divisor == 10 else 0,
        },
    }


def test_signed_minimum_is_treated_as_invalid_sentinel() -> None:
    point = _point(-32768, "s16", divisor=10)

    assert raw_value_is_sentinel(point) is True
    assert scaled_value(point) is None


def test_unsigned_maximum_is_treated_as_invalid_sentinel() -> None:
    point = _point(65535, "u16")

    assert raw_value_is_sentinel(point) is True
    assert scaled_value(point) is None


def test_explicitly_allowed_type_limit_is_preserved() -> None:
    point = _point(255, "u8", maximum=255)

    assert raw_value_is_sentinel(point) is False
    assert scaled_value(point) == 255


def test_explicitly_allowed_signed_minimum_is_preserved() -> None:
    point = _point(-32768, "s16", minimum=-32768, divisor=10)

    assert raw_value_is_sentinel(point) is False
    assert scaled_value(point) == -3276.8
