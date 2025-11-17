"""
Authentication endpoints.

Provides login and token refresh endpoints for API authentication.
"""

import os
import json
import logging
from typing import Optional
from pathlib import Path

from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.security import OAuth2PasswordRequestForm

from app.api.models.auth import Token, LoginRequest, RefreshTokenRequest
from app.api.auth import (
    verify_password,
    create_access_token,
    create_refresh_token,
    verify_token,
    ACCESS_TOKEN_EXPIRE_MINUTES
)

router = APIRouter()
logger = logging.getLogger(__name__)

# Credential storage path
CREDENTIALS_FILE = os.getenv(
    "API_CREDENTIALS_FILE",
    "configs/api_credentials.json"
)


def load_credentials() -> dict:
    """
    Load user credentials from JSON file.

    Returns:
        dict: Dictionary mapping usernames to hashed passwords
    """
    credentials_path = Path(CREDENTIALS_FILE)

    if not credentials_path.exists():
        logger.warning(f"Credentials file not found at {CREDENTIALS_FILE}")
        return {}

    try:
        with open(credentials_path, "r") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Failed to load credentials: {e}")
        return {}


def authenticate_user(username: str, password: str) -> Optional[str]:
    """
    Authenticate a user with username and password.

    Args:
        username: Username to authenticate
        password: Plain text password to verify

    Returns:
        Username if authenticated, None otherwise
    """
    credentials = load_credentials()

    if username not in credentials:
        logger.warning(f"Authentication failed: User '{username}' not found")
        return None

    hashed_password = credentials[username]

    if not verify_password(password, hashed_password):
        logger.warning(f"Authentication failed: Invalid password for user '{username}'")
        return None

    logger.info(f"User '{username}' authenticated successfully")
    return username


@router.post("/login", response_model=Token)
async def login(request: LoginRequest):
    """
    Authenticate and receive access and refresh tokens.

    Request body:
    ```json
    {
      "username": "admin",
      "password": "your-password"
    }
    ```

    Response:
    ```json
    {
      "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
      "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
      "token_type": "bearer",
      "expires_in": 1800
    }
    ```

    Use the access_token in subsequent requests:
    ```
    Authorization: Bearer <access_token>
    ```
    """
    username = authenticate_user(request.username, request.password)

    if not username:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Create tokens
    token_data = {"sub": username}
    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)

    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60  # Convert to seconds
    )


@router.post("/login/form", response_model=Token)
async def login_form(form_data: OAuth2PasswordRequestForm = Depends()):
    """
    OAuth2 compatible login endpoint (for Swagger UI).

    This endpoint uses OAuth2PasswordRequestForm which allows
    the Swagger UI's "Authorize" button to work properly.

    Form fields:
    - username: Username
    - password: Password
    """
    username = authenticate_user(form_data.username, form_data.password)

    if not username:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Create tokens
    token_data = {"sub": username}
    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)

    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )


@router.post("/refresh", response_model=Token)
async def refresh_token(request: RefreshTokenRequest):
    """
    Refresh an access token using a refresh token.

    Request body:
    ```json
    {
      "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGc..."
    }
    ```

    Response:
    ```json
    {
      "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
      "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
      "token_type": "bearer",
      "expires_in": 1800
    }
    ```
    """
    # Verify refresh token
    payload = verify_token(request.refresh_token)

    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Check token type
    token_type = payload.get("type")
    if token_type != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Extract username
    username = payload.get("sub")
    if not username:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Create new tokens
    token_data = {"sub": username}
    access_token = create_access_token(token_data)
    new_refresh_token = create_refresh_token(token_data)

    logger.info(f"Token refreshed for user '{username}'")

    return Token(
        access_token=access_token,
        refresh_token=new_refresh_token,
        token_type="bearer",
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )


@router.get("/verify")
async def verify_current_token(token: str):
    """
    Verify if a token is valid (for debugging).

    Query parameter:
    - token: JWT token to verify

    Response:
    ```json
    {
      "valid": true,
      "username": "admin",
      "token_type": "access",
      "expires": "2025-01-17T12:30:00Z"
    }
    ```
    """
    payload = verify_token(token)

    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return {
        "valid": True,
        "username": payload.get("sub"),
        "token_type": payload.get("type", "access"),
        "expires": payload.get("exp")
    }
