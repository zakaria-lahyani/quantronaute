"""
Position Monitor Service.

Monitors open positions and manages multi-target take profit execution.
Automatically closes portions of positions when TP levels are hit and
can move stop loss to breakeven or trailing levels.
"""

import logging
from typing import Dict, Optional, Any, List
from datetime import datetime
from collections import defaultdict

from app.services.base import EventDrivenService, ServiceStatus, HealthStatus
from app.infrastructure.event_bus import EventBus
from app.events.position_events import (
    PositionOpenedEvent,
    TPLevelHitEvent,
    PositionPartiallyClosedEvent,
    PositionFullyClosedEvent,
    StopLossMovedEvent,
)
from app.events.trade_events import TradesExecutedEvent


class PositionTracker:
    """
    Tracks a single position with its TP targets and state.
    """

    def __init__(
        self,
        ticket: int,
        symbol: str,
        direction: str,
        volume: float,
        open_price: float,
        stop_loss: Optional[float],
        tp_targets: List[Dict[str, Any]],
        magic: int = 0,
        group_id: Optional[str] = None,
    ):
        self.ticket = ticket
        self.symbol = symbol
        self.direction = direction  # 'long' or 'short'
        self.initial_volume = volume
        self.remaining_volume = volume
        self.open_price = open_price
        self.stop_loss = stop_loss
        self.tp_targets = tp_targets  # List of {level, percent, move_stop}
        self.magic = magic
        self.group_id = group_id

        # Track which TP levels have been hit
        self.hit_tp_levels: List[int] = []

        # State
        self.is_closed = False
        self.last_check_price: Optional[float] = None

    def get_next_tp_target(self) -> Optional[Dict[str, Any]]:
        """Get the next unhit TP target."""
        for idx, tp in enumerate(self.tp_targets):
            if idx not in self.hit_tp_levels:
                return {"index": idx, **tp}
        return None

    def mark_tp_hit(self, tp_index: int):
        """Mark a TP level as hit."""
        if tp_index not in self.hit_tp_levels:
            self.hit_tp_levels.append(tp_index)

    def calculate_volume_to_close(self, percent: float) -> float:
        """Calculate volume to close based on percentage."""
        return (percent / 100.0) * self.initial_volume


class PositionMonitorService(EventDrivenService):
    """
    Service for monitoring open positions and managing multi-target TPs.

    This service:
    - Tracks all open positions
    - Monitors current prices against TP levels
    - Partially closes positions when TP levels are hit
    - Moves stop loss to breakeven or trailing levels
    - Publishes events for all position state changes

    Configuration:
        symbol: Trading symbol (e.g., "BTCUSD") - for event filtering
        check_interval: How often to check positions (seconds)
        enable_tp_management: Enable multi-target TP (default: True)
        enable_sl_management: Enable SL movement (default: True)

    Example:
        ```python
        service = PositionMonitorService(
            event_bus=event_bus,
            client=mt5_client,
            config={
                "symbol": "BTCUSD",
                "check_interval": 1,  # Check every second
                "enable_tp_management": True,
                "enable_sl_management": True,
            }
        )
        service.start()
        ```
    """

    def __init__(
        self,
        event_bus: EventBus,
        client: Any,
        logger: Optional[logging.Logger] = None,
        config: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize PositionMonitorService.

        Args:
            event_bus: EventBus for publishing/subscribing events
            client: MT5 Client for managing positions
            logger: Optional logger
            config: Service configuration
        """
        super().__init__(
            service_name="PositionMonitorService",
            event_bus=event_bus,
            logger=logger,
            config=config,
        )

        self.client = client

        # Validate required config
        if not config:
            raise ValueError("PositionMonitorService requires configuration")

        if "symbol" not in config:
            raise ValueError("Configuration must include 'symbol'")

        # Configuration
        self.symbol = config["symbol"]
        self.check_interval = config.get("check_interval", 1)  # Check every second
        self.enable_tp_management = config.get("enable_tp_management", True)
        self.enable_sl_management = config.get("enable_sl_management", True)

        # Position tracking
        self.tracked_positions: Dict[int, PositionTracker] = {}

        # Metrics
        self._metrics["positions_monitored"] = 0
        self._metrics["tp_levels_hit"] = 0
        self._metrics["partial_closes_executed"] = 0
        self._metrics["stop_losses_moved"] = 0

        self.logger.info(
            f"PositionMonitorService initialized for {self.symbol} "
            f"(check_interval={self.check_interval}s, tp_mgmt={self.enable_tp_management}, "
            f"sl_mgmt={self.enable_sl_management})"
        )

    def start(self) -> None:
        """Start the PositionMonitorService."""
        self.logger.info(f"Starting {self.service_name}...")

        # Subscribe to TradesExecutedEvent to track new positions
        self.event_bus.subscribe(TradesExecutedEvent, self._on_trades_executed)

        self._status = ServiceStatus.RUNNING

        # Restore tracking for existing open positions (handles app reboot)
        self._restore_existing_positions()

        self.logger.info(f"{self.service_name} started successfully")

    def stop(self) -> None:
        """Stop the PositionMonitorService."""
        self.logger.info(f"Stopping {self.service_name}...")

        # Unsubscribe from events
        self.event_bus.unsubscribe(TradesExecutedEvent, self._on_trades_executed)

        self._status = ServiceStatus.STOPPED
        self.logger.info(f"{self.service_name} stopped")

    def health_check(self) -> HealthStatus:
        """
        Check service health.

        Returns:
            HealthStatus indicating current health
        """
        is_healthy = (
            self._status == ServiceStatus.RUNNING
            and len(self.tracked_positions) >= 0  # Service is functional
        )

        return HealthStatus(
            service_name=self.service_name,
            status=self._status,
            is_healthy=is_healthy,
            uptime_seconds=self.get_uptime_seconds(),
            last_error=self._last_error,
            metrics=self.get_metrics(),
        )

    def check_positions(self):
        """
        Check all tracked positions against current prices.

        This should be called periodically (e.g., every second) to monitor TP levels.
        """
        if not self.enable_tp_management:
            return

        if not self.tracked_positions:
            return

        try:
            # Get current price for symbol
            current_price = self._get_current_price()
            if current_price is None:
                return

            # Check each tracked position
            for ticket, position in list(self.tracked_positions.items()):
                if position.is_closed:
                    continue

                # Check if next TP target is hit
                self._check_tp_targets(position, current_price)

        except Exception as e:
            self.logger.error(f"Error checking positions: {e}", exc_info=True)
            self._handle_error(e)

    def _on_trades_executed(self, event: TradesExecutedEvent):
        """
        Handle TradesExecutedEvent to start tracking new positions.

        Args:
            event: TradesExecutedEvent containing executed trade info
        """
        # Only track positions for our symbol
        if event.symbol != self.symbol:
            return

        try:
            self.logger.info(f" [POSITION TRACK] Received TradesExecutedEvent for {event.symbol}")

            # Extract TP targets from metadata
            tp_targets = event.metadata.get("tp_targets", []) if event.metadata else []

            if not tp_targets:
                self.logger.debug(f"No TP targets for {event.symbol} - skipping monitoring")
                return

            # Get the tickets from executed orders
            tickets = event.metadata.get("tickets", []) if event.metadata else []

            if not tickets:
                self.logger.warning(f"No tickets found in TradesExecutedEvent metadata")
                return

            # Track each position
            for ticket in tickets:
                # Fetch position details from broker
                position_info = self._get_position_info(ticket)

                if not position_info:
                    self.logger.warning(f"Could not fetch position info for ticket {ticket}")
                    continue

                # Create position tracker
                direction = "long" if position_info["type"] == "buy" else "short"

                tracker = PositionTracker(
                    ticket=ticket,
                    symbol=self.symbol,
                    direction=direction,
                    volume=position_info["volume"],
                    open_price=position_info["price_open"],
                    stop_loss=position_info.get("sl"),
                    tp_targets=tp_targets,
                    magic=position_info.get("magic", 0),
                    group_id=event.metadata.get("group_id") if event.metadata else None,
                )

                self.tracked_positions[ticket] = tracker
                self._metrics["positions_monitored"] += 1

                self.logger.info(
                    f" [POSITION TRACKED] Ticket: {ticket}, "
                    f"Symbol: {self.symbol}, Direction: {direction}, "
                    f"Volume: {position_info['volume']}, "
                    f"TP Targets: {len(tp_targets)}"
                )

        except Exception as e:
            self.logger.error(f"Error tracking new positions: {e}", exc_info=True)
            self._handle_error(e)

    def _check_tp_targets(self, position: PositionTracker, current_price: float):
        """
        Check if any TP targets are hit for this position.

        Args:
            position: Position tracker
            current_price: Current market price
        """
        next_tp = position.get_next_tp_target()

        if not next_tp:
            # All TPs hit
            return

        tp_level = next_tp["level"]
        tp_index = next_tp["index"]

        # Check if TP is hit based on direction
        is_hit = False
        if position.direction == "long":
            is_hit = current_price >= tp_level
        else:  # short
            is_hit = current_price <= tp_level

        if is_hit:
            self.logger.info(
                f"🎯 [TP HIT] Ticket: {position.ticket}, TP{tp_index + 1}: {tp_level}, "
                f"Current: {current_price}"
            )

            # Publish TP hit event
            self.event_bus.publish(
                TPLevelHitEvent(
                    symbol=position.symbol,
                    ticket=position.ticket,
                    tp_level=tp_level,
                    current_price=current_price,
                    percent_to_close=next_tp["percent"],
                    move_stop=next_tp.get("move_stop", False),
                    timestamp=datetime.now(),
                )
            )

            # Execute partial close
            self._execute_partial_close(position, next_tp, current_price)

            # Mark TP as hit
            position.mark_tp_hit(tp_index)
            self._metrics["tp_levels_hit"] += 1

    def _execute_partial_close(
        self, position: PositionTracker, tp_target: Dict[str, Any], close_price: float
    ):
        """
        Execute partial position close.

        Args:
            position: Position tracker
            tp_target: TP target configuration
            close_price: Price at which to close
        """
        try:
            # Calculate volume to close
            volume_to_close = position.calculate_volume_to_close(tp_target["percent"])

            # Normalize volume
            from app.clients.mt5.utils import normalize_volume

            volume_to_close = normalize_volume(volume_to_close)

            self.logger.info(
                f"📤 [PARTIAL CLOSE] Ticket: {position.ticket}, "
                f"Closing {volume_to_close} lots ({tp_target['percent']}%)"
            )

            # Close partial position via client
            result = self.client.positions.close_position(
                symbol=position.symbol, ticket=position.ticket, volume=volume_to_close
            )

            if result.get("retcode") == 10009:  # Success
                # Update position tracker
                position.remaining_volume -= volume_to_close

                # Calculate profit
                if position.direction == "long":
                    profit = (close_price - position.open_price) * volume_to_close
                else:
                    profit = (position.open_price - close_price) * volume_to_close

                # Publish event
                self.event_bus.publish(
                    PositionPartiallyClosedEvent(
                        symbol=position.symbol,
                        original_ticket=position.ticket,
                        closed_volume=volume_to_close,
                        remaining_volume=position.remaining_volume,
                        close_price=close_price,
                        profit=profit,
                        tp_level=tp_target["level"],
                        timestamp=datetime.now(),
                    )
                )

                self._metrics["partial_closes_executed"] += 1

                self.logger.info(
                    f" [PARTIAL CLOSE SUCCESS] Profit: ${profit:+,.2f}, "
                    f"Remaining: {position.remaining_volume} lots"
                )

                # Move stop loss if configured
                if tp_target.get("move_stop", False) and self.enable_sl_management:
                    self._move_stop_loss_to_breakeven(position)

                # Check if position is fully closed
                if position.remaining_volume <= 0.01:  # Essentially zero
                    position.is_closed = True
                    del self.tracked_positions[position.ticket]

            else:
                self.logger.error(
                    f" [PARTIAL CLOSE FAILED] Ticket: {position.ticket}, "
                    f"Error: {result.get('comment')}"
                )

        except Exception as e:
            self.logger.error(f"Error executing partial close: {e}", exc_info=True)

    def _move_stop_loss_to_breakeven(self, position: PositionTracker):
        """
        Move stop loss to breakeven (entry price).

        Args:
            position: Position tracker
        """
        try:
            new_sl = position.open_price

            self.logger.info(
                f"🔒 [MOVE SL] Ticket: {position.ticket}, "
                f"Old SL: {position.stop_loss}, New SL: {new_sl} (Breakeven)"
            )

            # Modify position SL via client
            result = self.client.positions.modify_position(
                symbol=position.symbol, ticket=position.ticket, stop_loss=new_sl
            )

            if result.get("retcode") == 10009:  # Success
                old_sl = position.stop_loss
                position.stop_loss = new_sl

                # Publish event
                self.event_bus.publish(
                    StopLossMovedEvent(
                        symbol=position.symbol,
                        ticket=position.ticket,
                        old_stop_loss=old_sl,
                        new_stop_loss=new_sl,
                        reason="tp_hit",
                        timestamp=datetime.now(),
                    )
                )

                self._metrics["stop_losses_moved"] += 1

                self.logger.info(f" [SL MOVED] Stop loss moved to breakeven")

            else:
                self.logger.error(
                    f" [SL MOVE FAILED] Ticket: {position.ticket}, "
                    f"Error: {result.get('comment')}"
                )

        except Exception as e:
            self.logger.error(f"Error moving stop loss: {e}", exc_info=True)

    def _get_current_price(self) -> Optional[float]:
        """Get current bid/ask price for symbol."""
        try:
            price_data = self.client.symbols.get_symbol_price(self.symbol)
            # Use bid for long positions, ask for short positions
            # For simplicity, use bid (can be refined later)
            return price_data.get("bid")
        except Exception as e:
            self.logger.error(f"Error fetching current price: {e}")
            return None

    def _get_position_info(self, ticket: int) -> Optional[Dict[str, Any]]:
        """
        Get position information from broker.

        Args:
            ticket: Position ticket

        Returns:
            Position info dict or None
        """
        try:
            # Fetch position by ticket
            positions = self.client.positions.get_all_positions()
            for pos in positions:
                if pos.get("ticket") == ticket:
                    return pos
            return None
        except Exception as e:
            self.logger.error(f"Error fetching position info for {ticket}: {e}")
            return None

    def get_tracked_positions_count(self) -> int:
        """Get number of currently tracked positions."""
        return len([p for p in self.tracked_positions.values() if not p.is_closed])

    def _restore_existing_positions(self):
        """
        Restore tracking for existing open positions.

        This is called on service startup to handle app reboots.
        It fetches all open positions for this symbol and attempts to restore
        TP tracking if position metadata is available.
        """
        try:
            self.logger.info(f" [RESTORE] Checking for existing open positions for {self.symbol}...")

            # Get all open positions from broker
            all_positions = self.client.positions.get_open_positions()

            # Filter positions for this symbol
            symbol_positions = [
                pos for pos in all_positions if pos.get("symbol") == self.symbol
            ]

            if not symbol_positions:
                self.logger.info(f"  No existing positions found for {self.symbol}")
                return

            self.logger.info(f"  Found {len(symbol_positions)} existing position(s) for {self.symbol}")

            # Try to restore tracking for each position
            restored_count = 0
            for position in symbol_positions:
                ticket = position.get("ticket")
                comment = position.get("comment", "")

                # Try to extract metadata from position comment
                # Comment format: "Group_{group_id}" or strategy-specific
                tp_targets = self._extract_tp_targets_from_position(position)

                if tp_targets:
                    # Create tracker for this position
                    direction = "long" if position["type"] == "buy" else "short"

                    tracker = PositionTracker(
                        ticket=ticket,
                        symbol=self.symbol,
                        direction=direction,
                        volume=position["volume"],
                        open_price=position["price_open"],
                        stop_loss=position.get("sl"),
                        tp_targets=tp_targets,
                        magic=position.get("magic", 0),
                        group_id=self._extract_group_id_from_comment(comment),
                    )

                    self.tracked_positions[ticket] = tracker
                    restored_count += 1

                    self.logger.info(
                        f"   Restored tracking: Ticket {ticket}, "
                        f"Direction: {direction}, Volume: {position['volume']}, "
                        f"TP Targets: {len(tp_targets)}"
                    )
                else:
                    self.logger.warning(
                        f"    Cannot restore TP tracking for ticket {ticket} "
                        f"(no TP metadata available)"
                    )

            if restored_count > 0:
                self.logger.info(
                    f"🎉 [RESTORE COMPLETE] Restored tracking for {restored_count}/{len(symbol_positions)} positions"
                )
                self._metrics["positions_monitored"] += restored_count
            else:
                self.logger.warning(
                    f"  [RESTORE] No positions could be restored with TP tracking"
                )

        except Exception as e:
            self.logger.error(f"Error restoring existing positions: {e}", exc_info=True)
            # Don't fail startup - continue without restored positions

    def _extract_tp_targets_from_position(self, position: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Extract TP targets from position metadata.

        Since MT5 doesn't natively store custom TP targets, we have a few options:
        1. Store in position comment (limited space)
        2. Store in external database/file (recommended for production)
        3. Use default TP targets based on strategy

        For now, we'll use option 3: default TP targets based on magic number.
        You can enhance this by implementing persistent storage.

        Args:
            position: Position info from broker

        Returns:
            List of TP target dicts or empty list
        """
        magic = position.get("magic", 0)

        # Try to load TP targets from persistent storage
        tp_targets = self._load_tp_targets_from_storage(position["ticket"])

        if tp_targets:
            return tp_targets

        # Fallback: Use default TP targets based on entry price and direction
        # This is a simplified approach - enhance based on your strategy
        if magic != 0:  # Only restore if this is a strategy-managed position
            return self._get_default_tp_targets(position)

        return []

    def _load_tp_targets_from_storage(self, ticket: int) -> List[Dict[str, Any]]:
        """
        Load TP targets from persistent storage.

        TODO: Implement persistent storage (JSON file, database, etc.)
        For now, returns empty list.

        Args:
            ticket: Position ticket

        Returns:
            List of TP targets or empty list
        """
        # TODO: Implement persistent storage
        # Example: Load from JSON file keyed by ticket
        # Example: Load from database
        return []

    def _get_default_tp_targets(self, position: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Get default TP targets based on position parameters.

        This provides fallback TP targets when metadata is not available.
        Calculates conservative TP levels based on entry price.

        Args:
            position: Position info

        Returns:
            List of default TP targets
        """
        entry_price = position["price_open"]
        direction = position["type"]  # 'buy' or 'sell'

        # Calculate TP levels as percentage of entry
        # These are conservative defaults - adjust based on your strategy
        if direction == "buy":
            tp1 = entry_price * 1.05  # 5% profit
            tp2 = entry_price * 1.15  # 15% profit
        else:  # sell
            tp1 = entry_price * 0.95  # 5% profit
            tp2 = entry_price * 0.85  # 15% profit

        return [
            {"level": tp1, "percent": 80.0, "move_stop": True},
            {"level": tp2, "percent": 20.0, "move_stop": False},
        ]

    def _extract_group_id_from_comment(self, comment: str) -> Optional[str]:
        """
        Extract group ID from position comment.

        Comment format: "Group_{group_id}"

        Args:
            comment: Position comment

        Returns:
            Group ID or None
        """
        if comment and comment.startswith("Group_"):
            return comment.replace("Group_", "")
        return None

    def save_tp_targets_to_storage(self, ticket: int, tp_targets: List[Dict[str, Any]]):
        """
        Save TP targets to persistent storage for position restoration.

        This should be called when a position is opened to ensure TP targets
        can be restored after app reboot.

        TODO: Implement persistent storage

        Args:
            ticket: Position ticket
            tp_targets: List of TP target dicts
        """
        # TODO: Implement persistent storage
        # Example: Save to JSON file
        # Example: Save to database
        pass
