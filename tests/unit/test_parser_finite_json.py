"""Strict parser boundaries that can otherwise escape the JSON contract."""

import pytest

from generation.parser import ResponseValidationError, strict_json


@pytest.mark.parametrize(
    "raw",
    [
        '{"nested":{"number":1e400}}',
        '{"values":[-1e400]}',
        '{"value":NaN}',
        '{"value":Infinity}',
        '{"value":-Infinity}',
        '{"value":"\\ud800"}',
        '{"\\udfff":"value"}',
        '{"nested":["\\udc00"]}',
    ],
)
def test_nonfinite_and_non_utf8_values_are_rejected(raw):
    with pytest.raises(ResponseValidationError) as error:
        strict_json(raw)
    assert error.value.code == "INVALID_JSON"


def test_raw_unpaired_surrogate_is_rejected():
    with pytest.raises(ResponseValidationError) as error:
        strict_json('{"value":"' + chr(0xD800) + '"}')
    assert error.value.code == "INVALID_JSON"


def test_large_finite_numbers_and_complete_unicode_pair_are_preserved():
    assert strict_json('{"number":1e300,"value":"\\ud83d\\ude00"}') == {
        "number": 1e300,
        "value": "\U0001f600",
    }


def test_nested_duplicate_keys_remain_terminal_to_the_parser():
    with pytest.raises(ResponseValidationError) as error:
        strict_json('{"outer":{"verdict":"FAIL","verdict":"PASS"}}')
    assert error.value.code == "DUPLICATE_JSON_KEY"
