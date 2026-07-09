"""FastAPI dependency for JWT-protected endpoints.

Import ``get_current_user`` and add it as a ``Depends`` parameter to any
route that requires authentication. It will validate the bearer token and
return the resolved :class:`~app.models.user.User` instance, or raise a
401 response if the token is missing, invalid, or expired.
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError

from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.services.auth_service import AuthService

_bearer = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
) -> User:
    """Validate the bearer JWT and return the authenticated user.

    Raises:
        HTTPException 401: If the token is missing, malformed, expired,
            or the user no longer exists in the database.
    """

    token = credentials.credentials
    repo = UserRepository()
    service = AuthService(repo)

    try:
        user_id = service.verify_token(token)
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = repo.get(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user
