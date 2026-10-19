from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.schemas.common import EMAIL_RE, ORMModel


class _EmailMixin(BaseModel):
    email: str

    @field_validator("email")
    @classmethod
    def _validate_email(cls, value: str) -> str:
        value = value.strip().lower()
        if not EMAIL_RE.match(value):
            raise ValueError("Invalid email address")
        return value


class RegisterRequest(_EmailMixin):
    password: str = Field(min_length=8, max_length=128)
    name: str = Field(min_length=1, max_length=200)


class LoginRequest(_EmailMixin):
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class UserOut(ORMModel):
    id: str
    email: str
    name: str
    is_active: bool
    email_verified: bool
    created_at: datetime


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserOut
