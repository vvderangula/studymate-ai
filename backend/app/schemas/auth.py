"""Pydantic schemas for authentication endpoints."""

from pydantic import BaseModel, field_validator


class RegisterRequest(BaseModel):
    full_name: str
    email: str
    password: str

    @field_validator("full_name")
    @classmethod
    def full_name_not_empty(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Full name must not be empty.")
        return value

    @field_validator("email")
    @classmethod
    def email_valid(cls, value: str) -> str:
        value = value.strip().lower()
        if "@" not in value or "." not in value.split("@")[-1]:
            raise ValueError("Enter a valid email address.")
        return value

    @field_validator("password")
    @classmethod
    def password_min_length(cls, value: str) -> str:
        if len(value) < 8:
            raise ValueError("Password must be at least 8 characters.")
        return value


class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    full_name: str
    email: str
    role: str = "user"  # "admin" | "user"


class UserResponse(BaseModel):
    id: str
    full_name: str
    email: str
    role: str = "user"  # "admin" | "user"
