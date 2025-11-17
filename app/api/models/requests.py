"""
Request models for API endpoints.

This module defines Pydantic models for all API request bodies.
"""

from typing import Optional, List
from pydantic import BaseModel, Field


class EnableAutomationRequest(BaseModel):
    """Request to enable automated trading."""
    reason: Optional[str] = Field(None, description="Reason for enabling automation")


class DisableAutomationRequest(BaseModel):
    """Request to disable automated trading."""
    reason: Optional[str] = Field(None, description="Reason for disabling automation")


class ClosePositionRequest(BaseModel):
    """Request to close a position."""
    volume: Optional[float] = Field(None, description="Partial close volume (optional)")
    reason: Optional[str] = Field(None, description="Reason for closing")


class ModifyPositionRequest(BaseModel):
    """Request to modify position SL/TP."""
    stop_loss: Optional[float] = Field(None, description="New stop loss price")
    take_profit: Optional[float] = Field(None, description="New take profit price")


class PlaceOrderRequest(BaseModel):
    """
    Request to place a smart order (one-click trading).

    The system will automatically calculate:
    - Entry price (market price)
    - Position size (based on risk configuration)
    - Stop loss (based on ATR or configured method)
    - Take profit targets (single or multiple based on scaling config)
    - Apply position scaling if configured
    - Validate against risk limits
    """
    symbol: str = Field(..., description="Trading symbol")
    direction: str = Field(..., description="Trade direction (long/short)")
    strategy_name: Optional[str] = Field("manual", description="Strategy config to use for risk/sizing calculations")
    risk_override: Optional[float] = Field(None, description="Override risk percentage for this specific trade")


class UpdateRiskConfigRequest(BaseModel):
    """Request to update risk configuration."""
    max_positions: Optional[int] = Field(None, description="Maximum number of positions")
    max_daily_loss: Optional[float] = Field(None, description="Maximum daily loss")
    max_position_size: Optional[float] = Field(None, description="Maximum position size in lots")
    # TODO: Add more risk parameters as needed
