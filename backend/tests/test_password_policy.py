import pytest
from pydantic import ValidationError
from app.schemas import NewPassword


@pytest.mark.parametrize('password', ['İ2345678', 'K2345678', '12345678', 'abcdefgh'])
def test_password_policy_requires_an_actual_ascii_letter_and_digit(password):
    with pytest.raises(ValidationError):
        NewPassword(password=password, confirm_password=password)


def test_unicode_password_can_include_a_valid_ascii_letter_and_digit():
    value = 'CaféPassword123'
    assert NewPassword(password=value, confirm_password=value).password == value
