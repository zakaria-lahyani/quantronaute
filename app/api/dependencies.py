"""
FastAPI dependencies.

This module provides dependency injection functions for FastAPI endpoints.
"""

from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials, OAuth2PasswordBearer

from app.api.auth import verify_token

# HTTPBearer for general API usage
security = HTTPBearer()

# OAuth2PasswordBearer for Swagger UI compatibility
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login/form")


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> dict:
    """
    Dependency to get current authenticated user from JWT token.

    Args:
        credentials: HTTP Bearer token credentials

    Returns:
        dict: User information from token payload

    Raises:
        HTTPException: If token is invalid or expired
    """
    token = credentials.credentials
    payload = verify_token(token)

    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return payload


async def get_current_user_oauth2(token: str = Depends(oauth2_scheme)) -> dict:
    """
    Alternative dependency using OAuth2PasswordBearer (for Swagger UI).

    Args:
        token: JWT token from Authorization header

    Returns:
        dict: User information from token payload

    Raises:
        HTTPException: If token is invalid or expired
    """
    payload = verify_token(token)

    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return payload


async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Optional[dict]:
    """
    Dependency to get current user if authenticated, or None.

    Args:
        credentials: Optional HTTP Bearer token credentials

    Returns:
        Optional[dict]: User information or None if not authenticated
    """
    if credentials is None:
        return None

    return await get_current_user(credentials)
