"""HTTP routes for user registration and login."""

import logging

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.auth import get_current_user
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse, UserResponse
from app.services.auth_service import (
    AuthService,
    DuplicateEmailError,
    InvalidCredentialsError,
)

router = APIRouter(prefix="/auth", tags=["auth"])
logger = logging.getLogger(__name__)


def get_auth_service() -> AuthService:
    return AuthService(UserRepository())


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(
    request: RegisterRequest,
    service: AuthService = Depends(get_auth_service),
) -> TokenResponse:
    """Register a new user and return a JWT token.

    Responds with 400 for validation errors and 409 when the email is
    already registered.
    """

    try:
        user = service.register(request.full_name, request.email, request.password)
    except DuplicateEmailError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    token, _ = service.login(request.email, request.password)
    logger.info("New user registered: %s", user.email)
    return TokenResponse(
        access_token=token,
        user_id=user.id,
        full_name=user.full_name,
        email=user.email,
    )


@router.post("/login", response_model=TokenResponse)
def login(
    request: LoginRequest,
    service: AuthService = Depends(get_auth_service),
) -> TokenResponse:
    """Authenticate a user and return a JWT token.

    Responds with 401 for invalid credentials.
    """

    try:
        token, user = service.login(request.email, request.password)
    except InvalidCredentialsError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    logger.info("User logged in: %s", user.email)
    return TokenResponse(
        access_token=token,
        user_id=user.id,
        full_name=user.full_name,
        email=user.email,
    )


@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)) -> UserResponse:
    """Return the currently authenticated user's profile."""

    return UserResponse(
        id=current_user.id,
        full_name=current_user.full_name,
        email=current_user.email,
    )
