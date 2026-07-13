from typing import get_args

import pytest
from pydantic import ValidationError

from mof_bandgap.config import Settings

VALID_APP_ENV = get_args(Settings.model_fields["app_env"].annotation)
VALID_LOG_LEVEL = get_args(Settings.model_fields["log_level"].annotation)


@pytest.mark.parametrize("value", VALID_APP_ENV)
def test_accepts_valid_app_env(value: str) -> None:
    assert Settings.model_validate({"app_env": value}).app_env == value


@pytest.mark.parametrize("value", VALID_LOG_LEVEL)
def test_accepts_valid_log_level(value: str) -> None:
    assert Settings.model_validate({"log_level": value}).log_level == value


def test_rejects_invalid_app_env() -> None:
    with pytest.raises(ValidationError):
        Settings.model_validate({"app_env": "staging"})


def test_rejects_invalid_log_level() -> None:
    with pytest.raises(ValidationError):
        Settings.model_validate({"log_level": "TRACE"})


def test_rejects_unknown_field() -> None:
    with pytest.raises(ValidationError):
        Settings.model_validate({"unknown_field": "x"})
