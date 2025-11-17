"""
Authentication models.

This module defines Pydantic models for authentication.
"""

from typing import Optional
from pydantic import BaseModel, Field


class Token(BaseModel):
    """JWT token response."""
    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field("bearer", description="Token type")
    expires_in: int = Field(..., description="Token expiration time in seconds")


class TokenData(BaseModel):
    """Token payload data."""
    username: Optional[str] = None
    scopes: list[str] = []


class LoginRequest(BaseModel):
    """Login request."""
    username: str = Field(..., description="Username")
    password: str = Field(..., description="Password")


class RefreshTokenRequest(BaseModel):
    """Refresh token request."""
    refresh_token: str = Field(..., description="Refresh token")
