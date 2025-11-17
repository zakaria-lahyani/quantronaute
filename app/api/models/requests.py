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


class TriggerEntrySignalRequest(BaseModel):
    """
    Request to trigger a manual entry signal.

    This publishes an EntrySignalEvent with strategy_name="manual",
    which flows through the EXACT same pipeline as automated strategy signals:
    - EntryManager calculates position sizing based on risk config
    - SL/TP calculated based on configuration (ATR, fixed, etc.)
    - Position scaling applied if configured
    - Risk limits validated
    - Execution through TradeExecutionService → MT5Client

    User provides ONLY symbol and direction - everything else is handled
    by the existing trading infrastructure.
    """
    symbol: str = Field(..., description="Trading symbol")
    direction: str = Field(..., description="Trade direction (long/short)")


class TriggerExitSignalRequest(BaseModel):
    """
    Request to trigger a manual exit signal.

    This publishes an ExitSignalEvent with strategy_name="manual",
    which closes positions through the standard exit logic.
    """
    symbol: str = Field(..., description="Trading symbol")
    direction: str = Field(..., description="Position direction to exit (long/short)")
    reason: Optional[str] = Field("manual", description="Reason for exit")


class UpdateRiskConfigRequest(BaseModel):
    """Request to update risk configuration."""
    max_positions: Optional[int] = Field(None, description="Maximum number of positions")
    max_daily_loss: Optional[float] = Field(None, description="Maximum daily loss")
    max_position_size: Optional[float] = Field(None, description="Maximum position size in lots")
    # TODO: Add more risk parameters as needed
