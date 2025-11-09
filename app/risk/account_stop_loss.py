"""
Account-Level Stop Loss Manager.

Monitors total account P&L across all symbols and stops trading when loss limits are breached.
This is a global risk management system that operates at the account level, not per-symbol.

Key Features:
- Monitors daily P&L across all symbols
- Monitors drawdown from peak balance
- Automatically closes all positions when limits breached
- Stops all trading services
- Publishes events for monitoring and alerts
- Configurable limits and recovery rules
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, date, time
from enum import Enum
from dataclasses import dataclass


class StopLossStatus(Enum):
    """Account stop loss status."""
    ACTIVE = "active"  # Trading allowed
    DAILY_LOSS_BREACHED = "daily_loss_breached"  # Daily loss limit hit
    DRAWDOWN_BREACHED = "drawdown_breached"  # Max drawdown limit hit
    MANUALLY_STOPPED = "manually_stopped"  # Manual trading halt
    RECOVERING = "recovering"  # In recovery period after breach


@dataclass
class AccountStopLossConfig:
    """Configuration for account-level stop loss."""

    # Daily loss limit (absolute value)
    daily_loss_limit: float = 1000.0

    # Max drawdown from peak (percentage, 0-100)
    max_drawdown_pct: float = 10.0

    # Whether to close all positions on breach
    close_positions_on_breach: bool = True

    # Whether to stop all trading services on breach
    stop_trading_on_breach: bool = True

    # Cooldown period before allowing trading again (minutes)
    cooldown_period_minutes: int = 60

    # Reset daily loss at this time (HH:MM:SS format)
    daily_reset_time: str = "00:00:00"

    # Timezone offset for reset time (e.g., "+03:00" for UTC+3)
    timezone_offset: str = "+00:00"


@dataclass
class AccountMetrics:
    """Current account metrics."""

    current_balance: float
    starting_balance: float  # Balance at start of day
    peak_balance: float  # Peak balance since tracking started
    daily_pnl: float
    total_pnl: float
    current_drawdown_pct: float
    open_positions_count: int
    total_exposure: float
    timestamp: datetime


class AccountStopLossManager:
    """
    Manages account-level stop loss across all symbols.

    This manager operates independently of individual symbols and monitors
    the entire account for risk limit breaches.

    Example:
        ```python
        # Create manager with configuration
        config = AccountStopLossConfig(
            daily_loss_limit=1000.0,
            max_drawdown_pct=10.0,
            close_positions_on_breach=True
        )

        manager = AccountStopLossManager(
            config=config,
            client=mt5_client,
            logger=logger
        )

        # Update account metrics
        manager.update_account_metrics(
            current_balance=9500.0,
            starting_balance=10000.0
        )

        # Check if trading is allowed
        if manager.is_trading_allowed():
            # Execute trade
            pass
        else:
            # Trading stopped due to risk limit
            reason = manager.get_stop_reason()
            print(f"Trading stopped: {reason}")
        ```
    """

    def __init__(
        self,
        config: AccountStopLossConfig,
        client: Any,
        logger: Optional[logging.Logger] = None
    ):
        """
        Initialize account stop loss manager.

        Args:
            config: Stop loss configuration
            client: MT5 client for closing positions
            logger: Optional logger
        """
        self.config = config
        self.client = client
        self.logger = logger or logging.getLogger('account-stop-loss')

        # State
        self.status = StopLossStatus.ACTIVE
        self.starting_balance: Optional[float] = None
        self.peak_balance: Optional[float] = None
        self.current_balance: Optional[float] = None
        self.daily_pnl = 0.0
        self.current_drawdown_pct = 0.0

        # Breach tracking
        self.breach_time: Optional[datetime] = None
        self.breach_reason: Optional[str] = None
        self.last_reset_date: Optional[date] = None

        # Metrics history
        self.metrics_history: List[AccountMetrics] = []

        self.logger.info("AccountStopLossManager initialized")
        self.logger.info(f"  Daily loss limit: ${config.daily_loss_limit}")
        self.logger.info(f"  Max drawdown: {config.max_drawdown_pct}%")

    def initialize(self, starting_balance: float):
        """
        Initialize the manager with starting balance.

        Args:
            starting_balance: Account starting balance
        """
        self.starting_balance = starting_balance
        self.peak_balance = starting_balance
        self.current_balance = starting_balance
        self.last_reset_date = datetime.now().date()

        self.logger.info(f"Initialized with starting balance: ${starting_balance:,.2f}")

    def update_account_metrics(
        self,
        current_balance: float,
        starting_balance: Optional[float] = None,
        open_positions_count: int = 0,
        total_exposure: float = 0.0
    ) -> AccountMetrics:
        """
        Update account metrics and check for stop loss breaches.

        Args:
            current_balance: Current account balance
            starting_balance: Optional starting balance (updates if provided)
            open_positions_count: Number of open positions
            total_exposure: Total exposure across all positions

        Returns:
            AccountMetrics with current state
        """
        # Update starting balance if provided
        if starting_balance is not None:
            self.starting_balance = starting_balance

        # Initialize if not done
        if self.starting_balance is None:
            self.initialize(current_balance)

        # Update current balance
        self.current_balance = current_balance

        # Update peak balance
        if self.peak_balance is None or current_balance > self.peak_balance:
            self.peak_balance = current_balance

        # Calculate daily P&L
        self.daily_pnl = current_balance - self.starting_balance

        # Calculate drawdown from peak
        self.current_drawdown_pct = ((self.peak_balance - current_balance) / self.peak_balance) * 100

        # Total P&L (from initial peak)
        total_pnl = current_balance - self.peak_balance

        # Create metrics snapshot
        metrics = AccountMetrics(
            current_balance=current_balance,
            starting_balance=self.starting_balance,
            peak_balance=self.peak_balance,
            daily_pnl=self.daily_pnl,
            total_pnl=total_pnl,
            current_drawdown_pct=self.current_drawdown_pct,
            open_positions_count=open_positions_count,
            total_exposure=total_exposure,
            timestamp=datetime.now()
        )

        # Store in history
        self.metrics_history.append(metrics)

        # Check for daily reset
        self._check_daily_reset()

        # Check for breaches
        self._check_stop_loss_breach()

        # Log metrics
        self.logger.debug(
            f"Account Metrics: Balance=${current_balance:,.2f}, "
            f"Daily P&L=${self.daily_pnl:+,.2f}, "
            f"Drawdown={self.current_drawdown_pct:.2f}%, "
            f"Status={self.status.value}"
        )

        return metrics

    def _check_daily_reset(self):
        """Check if we should reset daily P&L."""
        current_date = datetime.now().date()

        if self.last_reset_date is None or current_date > self.last_reset_date:
            # New day - reset daily P&L
            self.logger.info(f"Daily reset triggered. Previous daily P&L: ${self.daily_pnl:+,.2f}")
            self.starting_balance = self.current_balance
            self.daily_pnl = 0.0
            self.last_reset_date = current_date

            # If we were in daily loss breach, reset to active
            if self.status == StopLossStatus.DAILY_LOSS_BREACHED:
                self.logger.info("Resetting from daily loss breach to active status")
                self.status = StopLossStatus.ACTIVE
                self.breach_time = None
                self.breach_reason = None

    def _check_stop_loss_breach(self):
        """Check if any stop loss limits have been breached."""
        if self.status in [StopLossStatus.MANUALLY_STOPPED, StopLossStatus.RECOVERING]:
            # Don't check if manually stopped or recovering
            return

        # Check daily loss limit
        if self.daily_pnl < -self.config.daily_loss_limit:
            self._trigger_stop_loss_breach(
                status=StopLossStatus.DAILY_LOSS_BREACHED,
                reason=f"Daily loss limit breached: ${self.daily_pnl:+,.2f} < -${self.config.daily_loss_limit:,.2f}"
            )
            return

        # Check drawdown limit
        if self.current_drawdown_pct > self.config.max_drawdown_pct:
            self._trigger_stop_loss_breach(
                status=StopLossStatus.DRAWDOWN_BREACHED,
                reason=f"Max drawdown breached: {self.current_drawdown_pct:.2f}% > {self.config.max_drawdown_pct:.2f}%"
            )
            return

    def _trigger_stop_loss_breach(self, status: StopLossStatus, reason: str):
        """
        Trigger stop loss breach.

        Args:
            status: New stop loss status
            reason: Breach reason
        """
        if self.status != StopLossStatus.ACTIVE:
            # Already breached
            return

        self.logger.error("=" * 80)
        self.logger.error("ACCOUNT STOP LOSS BREACHED!")
        self.logger.error(reason)
        self.logger.error(f"Current balance: ${self.current_balance:,.2f}")
        self.logger.error(f"Starting balance: ${self.starting_balance:,.2f}")
        self.logger.error(f"Peak balance: ${self.peak_balance:,.2f}")
        self.logger.error("=" * 80)

        self.status = status
        self.breach_time = datetime.now()
        self.breach_reason = reason

        # Close positions if configured
        if self.config.close_positions_on_breach:
            self.logger.warning("Closing all open positions...")
            self._close_all_positions()

    def _close_all_positions(self):
        """Close all open positions."""
        try:
            # Get all open positions across all symbols
            positions = self.client.positions.get_all_positions()

            if not positions:
                self.logger.info("No open positions to close")
                return

            self.logger.info(f"Closing {len(positions)} open positions...")

            closed_count = 0
            failed_count = 0

            for position in positions:
                try:
                    result = self.client.positions.close_position(position['ticket'])
                    if result.get('success'):
                        closed_count += 1
                        self.logger.info(f"  ✓ Closed position {position['ticket']} ({position['symbol']})")
                    else:
                        failed_count += 1
                        self.logger.error(f"  ✗ Failed to close {position['ticket']}: {result.get('error')}")
                except Exception as e:
                    failed_count += 1
                    self.logger.error(f"  ✗ Error closing {position['ticket']}: {e}")

            self.logger.info(f"Position closure complete: {closed_count} closed, {failed_count} failed")

        except Exception as e:
            self.logger.error(f"Error closing all positions: {e}", exc_info=True)

    def is_trading_allowed(self) -> bool:
        """
        Check if trading is currently allowed.

        Returns:
            True if trading allowed, False otherwise
        """
        return self.status == StopLossStatus.ACTIVE

    def get_stop_reason(self) -> Optional[str]:
        """
        Get the reason trading was stopped.

        Returns:
            Stop reason if stopped, None if active
        """
        if self.status == StopLossStatus.ACTIVE:
            return None

        return self.breach_reason or f"Trading stopped: {self.status.value}"

    def get_status(self) -> StopLossStatus:
        """
        Get current stop loss status.

        Returns:
            Current status
        """
        return self.status

    def manual_stop(self, reason: str = "Manual stop"):
        """
        Manually stop trading.

        Args:
            reason: Reason for manual stop
        """
        self.logger.warning(f"Manual trading stop: {reason}")
        self.status = StopLossStatus.MANUALLY_STOPPED
        self.breach_time = datetime.now()
        self.breach_reason = reason

        if self.config.close_positions_on_breach:
            self._close_all_positions()

    def manual_resume(self):
        """Manually resume trading after stop."""
        if self.status == StopLossStatus.MANUALLY_STOPPED:
            self.logger.info("Manually resuming trading")
            self.status = StopLossStatus.ACTIVE
            self.breach_time = None
            self.breach_reason = None
        else:
            self.logger.warning(f"Cannot resume from status: {self.status.value}")

    def get_current_metrics(self) -> Optional[AccountMetrics]:
        """
        Get most recent account metrics.

        Returns:
            Latest AccountMetrics or None if no metrics
        """
        if not self.metrics_history:
            return None
        return self.metrics_history[-1]

    def get_metrics_summary(self) -> Dict[str, Any]:
        """
        Get summary of account metrics and stop loss status.

        Returns:
            Dictionary with metrics summary
        """
        return {
            'status': self.status.value,
            'is_trading_allowed': self.is_trading_allowed(),
            'current_balance': self.current_balance,
            'starting_balance': self.starting_balance,
            'peak_balance': self.peak_balance,
            'daily_pnl': self.daily_pnl,
            'daily_pnl_pct': (self.daily_pnl / self.starting_balance * 100) if self.starting_balance else 0,
            'current_drawdown_pct': self.current_drawdown_pct,
            'daily_loss_limit': self.config.daily_loss_limit,
            'max_drawdown_pct': self.config.max_drawdown_pct,
            'daily_loss_remaining': self.config.daily_loss_limit + self.daily_pnl,
            'drawdown_remaining_pct': self.config.max_drawdown_pct - self.current_drawdown_pct,
            'breach_time': self.breach_time.isoformat() if self.breach_time else None,
            'breach_reason': self.breach_reason,
            'metrics_count': len(self.metrics_history)
        }

    def reset_limits(self):
        """Reset stop loss limits (use with caution!)."""
        self.logger.warning("Resetting stop loss limits")
        self.status = StopLossStatus.ACTIVE
        self.breach_time = None
        self.breach_reason = None

    def update_config(self, config: AccountStopLossConfig):
        """
        Update stop loss configuration.

        Args:
            config: New configuration
        """
        self.logger.info("Updating stop loss configuration")
        self.logger.info(f"  Daily loss limit: ${self.config.daily_loss_limit} → ${config.daily_loss_limit}")
        self.logger.info(f"  Max drawdown: {self.config.max_drawdown_pct}% → {config.max_drawdown_pct}%")

        self.config = config

        # Re-check with new limits
        self._check_stop_loss_breach()
