"""Authentication service: user registration, login, and JWT operations."""

import uuid
from datetime import datetime, timedelta, timezone

import bcrypt
from jose import JWTError, jwt

from app.core.config import settings
from app.models.user import User
from app.repositories.user_repository import UserRepository


def _hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def _verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode(), hashed.encode())
    except Exception:
        return False


class AuthError(Exception):
    """Base class for authentication errors."""


class DuplicateEmailError(AuthError):
    """Raised when the email is already registered."""


class InvalidCredentialsError(AuthError):
    """Raised when email or password is incorrect."""


class AccountNotFoundError(InvalidCredentialsError):
    """No account is registered with the email."""


class WrongPasswordError(InvalidCredentialsError):
    """The account exists but the password does not match."""


class AuthService:
    """Handles user registration, login, and JWT token lifecycle.

    This service is the single home for all authentication business logic.
    Password hashing, credential validation, and token operations all live
    here and are not permitted to leak into routes or other services.
    """

    def __init__(self, repository: UserRepository) -> None:
        self._repo = repository

    def register(self, full_name: str, email: str, password: str) -> User:
        """Create a new user account.

        Raises:
            DuplicateEmailError: If the email is already taken.
        """

        if self._repo.get_by_email(email):
            raise DuplicateEmailError("An account with this email already exists.")

        user = User(
            id=uuid.uuid4().hex,
            full_name=full_name.strip(),
            email=email.lower().strip(),
            password_hash=_hash_password(password),
            created_at=datetime.now(timezone.utc),
        )
        self._repo.create(user)
        return user

    def login(self, email: str, password: str) -> tuple[str, User]:
        """Validate credentials and return a JWT token + the user.

        Raises:
            AccountNotFoundError: If no account uses this email.
            WrongPasswordError: If the password does not match.
        """

        user = self._repo.get_by_email(email.lower().strip())
        if not user:
            raise AccountNotFoundError(
                "No account found with this email. Check the address or create an account."
            )
        if not _verify_password(password, user.password_hash):
            raise WrongPasswordError("Incorrect password. Try again.")

        token = _create_token(user.id)
        return token, user

    def verify_token(self, token: str) -> str:
        """Decode a JWT and return the user_id (``sub`` claim).

        Raises:
            JWTError: If the token is invalid or expired.
        """

        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
        user_id: str | None = payload.get("sub")
        if not user_id:
            raise JWTError("Token payload missing subject.")
        return user_id


def _create_token(user_id: str) -> str:
    """Sign and return a JWT for the given user."""

    expire = datetime.now(timezone.utc) + timedelta(days=settings.jwt_expire_days)
    return jwt.encode(
        {"sub": user_id, "exp": expire},
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )
