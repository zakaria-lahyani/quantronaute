"""
Response models for API endpoints.

This module defines Pydantic models for all API responses.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field


class AutomationStatusResponse(BaseModel):
    """Response with automation status."""
    enabled: bool = Field(..., description="Whether automation is enabled")
    changed_at: Optional[datetime] = Field(None, description="When status last changed")
    reason: Optional[str] = Field(None, description="Reason for current state")


class PositionResponse(BaseModel):
    """Response with position details."""
    position_id: int = Field(..., description="Position ticket number")
    symbol: str = Field(..., description="Trading symbol")
    direction: str = Field(..., description="Position direction (long/short)")
    volume: float = Field(..., description="Position size in lots")
    entry_price: float = Field(..., description="Entry price")
    current_price: float = Field(..., description="Current market price")
    profit: float = Field(..., description="Current profit/loss")
    stop_loss: Optional[float] = Field(None, description="Stop loss price")
    take_profit: Optional[float] = Field(None, description="Take profit price")
    open_time: datetime = Field(..., description="When position was opened")


class PositionListResponse(BaseModel):
    """Response with list of positions."""
    positions: List[PositionResponse] = Field(..., description="List of open positions")
    total_count: int = Field(..., description="Total number of positions")


class OrderPlacedResponse(BaseModel):
    """Response after placing an order."""
    success: bool = Field(..., description="Whether order was placed successfully")
    order_id: Optional[int] = Field(None, description="Broker-assigned order ID")
    message: str = Field(..., description="Status message")


class IndicatorValueResponse(BaseModel):
    """Response with indicator values."""
    symbol: str = Field(..., description="Trading symbol")
    timeframe: str = Field(..., description="Timeframe")
    indicators: Dict[str, Any] = Field(..., description="Current indicator values")
    timestamp: datetime = Field(..., description="When indicators were calculated")


class StrategyConditionResponse(BaseModel):
    """Response with strategy condition evaluation (NEW feature)."""
    symbol: str = Field(..., description="Trading symbol")
    strategy_name: str = Field(..., description="Strategy name")
    would_trigger: bool = Field(..., description="Would strategy trigger entry now")
    conditions: List[Dict[str, Any]] = Field(..., description="Condition evaluation details")
    blocking_conditions: List[str] = Field([], description="Conditions preventing trigger")
    timestamp: datetime = Field(..., description="Evaluation timestamp")


class AccountInfoResponse(BaseModel):
    """Response with account information."""
    balance: float = Field(..., description="Account balance")
    equity: float = Field(..., description="Account equity")
    margin: float = Field(..., description="Used margin")
    free_margin: float = Field(..., description="Free margin")
    margin_level: float = Field(..., description="Margin level percentage")
    profit: float = Field(..., description="Floating profit/loss")


class SystemStatusResponse(BaseModel):
    """Response with system status."""
    status: str = Field(..., description="Overall system status")
    uptime: float = Field(..., description="System uptime in seconds")
    event_bus_active: bool = Field(..., description="Whether EventBus is active")
    trading_active: bool = Field(..., description="Whether trading is active")
    metrics: Dict[str, Any] = Field({}, description="System metrics")


class ErrorResponse(BaseModel):
    """Response for errors."""
    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Error message")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")
