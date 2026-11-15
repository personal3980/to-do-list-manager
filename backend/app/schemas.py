"""Server-side validation is independent of browser validation."""
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_serializer, field_validator, model_validator


class EmailInput(BaseModel):
    email: EmailStr = Field(max_length=254)

    @field_validator('email', mode='before')
    @classmethod
    def normalize_email(cls, value):
        return value.strip().lower() if isinstance(value, str) else value


class LoginInput(EmailInput):
    password: str = Field(min_length=1, max_length=128)


class NewPassword(BaseModel):
    password: str = Field(min_length=8, max_length=128)
    confirm_password: str = Field(min_length=8, max_length=128)

    @field_validator('password')
    @classmethod
    def password_strength(cls, value):
        if not any('a' <= c.lower() <= 'z' for c in value) or not any('0' <= c <= '9' for c in value):
            raise ValueError('Use at least one letter and one number.')
        return value

    @model_validator(mode='after')
    def passwords_match(self):
        if self.password != self.confirm_password:
            raise ValueError('Passwords do not match.')
        return self


class SignupInput(NewPassword, EmailInput):
    name: str = Field(min_length=2, max_length=80)

    @field_validator('name', mode='before')
    @classmethod
    def trim_name(cls, value):
        return value.strip() if isinstance(value, str) else value


class ResetInput(NewPassword):
    token: str = Field(pattern=r'^[A-Za-z0-9_-]{43}$')


class UserOutput(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    email: str


# Tasks use calendar dates; timestamps are serialized explicitly as UTC below.


class TaskInput(BaseModel):
    model_config = ConfigDict(extra='forbid')
    title: str = Field(min_length=1, max_length=120)
    notes: str = Field(default='', max_length=500)
    priority: Literal['low', 'medium', 'high'] = 'medium'
    due: date | None = Field(default=None, ge=date(1000, 1, 1))
    completed: bool = Field(default=False, strict=True)

    @field_validator('title', mode='before')
    @classmethod
    def trim_title(cls, value):
        return value.strip() if isinstance(value, str) else value


class TaskImport(TaskInput):
    legacy_id: str = Field(min_length=1, max_length=100)


class TaskStatus(BaseModel):
    model_config = ConfigDict(extra='forbid')
    completed: bool = Field(strict=True)


class TaskOutput(TaskInput):
    model_config = ConfigDict(from_attributes=True)
    id: str
    created_at: datetime

    @field_serializer('created_at')
    def utc_timestamp(self, value):
        return value.isoformat() + 'Z'
