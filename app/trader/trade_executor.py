"""
Refactored Trade Executor with single responsibility components.
"""

import logging
from datetime import datetime
from typing import List

from app.clients.mt5.models.history import ClosedPosition
from app.clients.mt5.models.order import PendingOrder
from app.clients.mt5.models.response import Position
from app.strategy_builder.data.dtos import Trades, EntryDecision, ExitDecision
from app.trader.live_trader import LiveTrader
from app.trader.risk_manager.models import ScalingConfig
from app.trader.risk_manager.risk_calculator import RiskCalculator
from app.utils.config import LoadEnvironmentVariables
from app.utils.date_helper import DateHelper

# Import our single responsibility components
from .components.exit_manager import ExitManager
from .components.duplicate_filter import DuplicateFilter
from .components.pnl_calculator import PnLCalculator
from .components.risk_monitor import RiskMonitor
from .components.order_executor import OrderExecutor
from .trade_restriction import TradeRestriction
from .suspension_store import SuspensionStore, SuspendedItem


class TradeExecutor:
    """
    Orchestrates trade execution using single responsibility components.
    Single responsibility: Orchestration and coordination.
    """
    
    def __init__(self, mode: str, config: LoadEnvironmentVariables, **kwargs):
        self.mode = mode
        self.config = config
        self.logger = logging.getLogger('trade-executor')
        
        # Initialize scaling configuration
        scaling_config = ScalingConfig(
            num_entries=config.POSITION_SPLIT,
            scaling_type=config.SCALING_TYPE,
            entry_spacing=config.ENTRY_SPACING,
            max_risk_per_group=config.RISK_PER_GROUP
        )
        
        # Initialize risk calculator
        risk_calculator = RiskCalculator(scaling_config)

        # Initialize trade restriction
        self.trade_restriction = TradeRestriction(
            restriction_path=config.RESTRICTION_CONF_FOLDER_PATH,
            default_close_time_str=config.DEFAULT_CLOSE_TIME,
            news_duration=config.NEWS_RESTRICTION_DURATION,
            market_close_duration=config.MARKET_CLOSE_RESTRICTION_DURATION
        )

        # Initialize trader
        if mode == 'live':
            if 'client' not in kwargs:
                raise ValueError("Live trading requires client")
            trader = LiveTrader(kwargs['client'])
        else:
            raise ValueError(f"Unsupported mode: {mode}")
        
        # Initialize single responsibility components
        self.exit_manager = ExitManager(trader, self.logger)
        self.duplicate_filter = DuplicateFilter(self.logger)
        self.pnl_calculator = PnLCalculator(self.logger)
        self.risk_monitor = RiskMonitor(
            trader, 
            config.DAILY_LOSS_LIMIT, 
            self.pnl_calculator, 
            self.logger
        )
        self.order_executor = OrderExecutor(
            trader, 
            risk_calculator, 
            config.SYMBOL, 
            self.logger
        )
        
        # Keep reference to trader for data fetching
        self.trader = trader
        self.trade_authorized = True
        
        # Initialize suspension store and state tracking
        self.suspension_store = SuspensionStore(self.logger)
        self.last_news_state: bool | None = None
    def cancel(self):
        self.trader.cancel_all_pending_orders()

    def manage(self, trades: Trades, date_helper: DateHelper) -> None:
        """
        Main orchestration method - coordinates all components.
        
        Args:
            trades: Trade signals to process
            date_helper: Date helper for time calculations
        """
        self.logger.info("=== TRADE EXECUTION CYCLE START ===")
        
        try:
            current_time = date_helper.now()
            
            # 1. Fetch current market state
            market_state = self._fetch_market_state(date_helper)
            
            # 2. Apply trading restrictions FIRST
            self._apply_trading_restrictions(current_time, market_state)
            
            # 3. Process exits first
            self._process_exits(trades.exits, market_state['open_positions'])
            
            # 4. Check risk limits
            risk_breached = self._check_risk_limits(
                market_state['open_positions'], 
                market_state['closed_positions']
            )
            
            # 5. Process entries only if authorized and risk is acceptable
            if self.trade_authorized and not risk_breached:
                self._process_entries(
                    trades.entries, 
                    market_state['open_positions'], 
                    market_state['pending_orders']
                )
            elif not self.trade_authorized:
                self.logger.warning("Entry processing blocked - trade not authorized (restrictions active)")
            elif risk_breached:
                self.logger.warning("Entry processing skipped due to risk limit breach")
            
        except Exception as e:
            self.logger.error(f"Error in trade execution cycle: {e}")
        
        self.logger.info("=== TRADE EXECUTION CYCLE END ===")
    
    def _fetch_market_state(self, date_helper: DateHelper) -> dict:
        """Fetch current market state data."""
        start_date = f"{date_helper.get_date_days_ago(0)}T00:00:00Z"
        end_date = f"{date_helper.get_date_days_ago(-1)}T00:00:00Z"
        
        return {
            'closed_positions': self.trader.get_closed_positions(start_date, end_date),
            'pending_orders': self.trader.get_pending_orders(self.config.SYMBOL),
            'open_positions': self.trader.get_open_positions(self.config.SYMBOL)
        }
    
    def _process_exits(self, exits: List[ExitDecision], open_positions: List[Position]) -> None:
        """Process exit signals using ExitManager."""
        if exits:
            self.logger.info(f"Processing {len(exits)} exit signals")
            self.exit_manager.process_exits(exits, open_positions)
        else:
            self.logger.debug("No exit signals to process")

    def _apply_trading_restrictions(self, current_time: datetime, market_state: dict) -> None:
        """
        Apply all trading restrictions (news and market closing).
        
        Args:
            current_time: Current datetime
            market_state: Current market state with positions and orders
        """
        # Check news events
        self._check_news_event(current_time, market_state)
        
        # Check market closing
        self._check_market_closing(current_time, market_state)
    
    def _check_news_event(self, current_time: datetime, market_state: dict) -> None:
        """
        Handle news event restrictions with suspension and restoration logic.
        
        Args:
            current_time: Current datetime
            market_state: Current market state with positions and orders
        """
        is_news_active = self.trade_restriction.is_news_block_active(current_time)
        
        # Detect state transitions
        if self.last_news_state != is_news_active:
            if is_news_active:  # Transition to news block (False -> True)
                self.logger.warning("News event started - suspending trading activity")
                self._suspend_trading_activity(market_state)
                self.trade_authorized = False
                
            elif self.last_news_state is True:  # Transition from news block (True -> False)
                self.logger.info("News event ended - restoring suspended trading activity")
                self._restore_suspended_activity()
                self.trade_authorized = True
            
            self.last_news_state = is_news_active

    def _check_market_closing(self, current_time: datetime, market_state: dict) -> None:
        """
        Handle market closing restrictions for daily accounts.
        
        Args:
            current_time: Current datetime
            market_state: Current market state with positions and orders
        """
        is_closing_soon = self.trade_restriction.is_market_closing_soon(self.config.SYMBOL, current_time)
        
        if is_closing_soon and self.config.ACCOUNT_TYPE == "daily":
            self.logger.warning("Market closing soon - executing daily account closure")
            self._execute_daily_closure(market_state)
            self.trade_authorized = False
        elif not is_closing_soon and self.config.ACCOUNT_TYPE == "daily":
            # Market is open for daily accounts - restore trade authorization if no other restrictions
            if not self.trade_restriction.is_news_block_active(current_time):
                self.trade_authorized = True


    def _check_risk_limits(
        self, 
        open_positions: List[Position], 
        closed_positions: List[ClosedPosition]
    ) -> bool:
        """Check risk limits using RiskMonitor."""
        return self.risk_monitor.check_catastrophic_loss_limit(
            open_positions, closed_positions
        )
    
    def _process_entries(
        self, 
        entries: List[EntryDecision], 
        open_positions: List[Position],
        pending_orders: List[PendingOrder]
    ) -> None:
        """Process entry signals with duplicate filtering."""
        if not entries:
            self.logger.debug("No entry signals to process")
            return
        
        self.logger.info(f"Processing {len(entries)} entry signals")
        
        # Check if trading is authorized
        if not self.trade_authorized:
            self.logger.warning("Entry processing blocked - trade not authorized")
            return

        # Filter duplicates
        filtered_entries = self.duplicate_filter.filter_entries(
            entries, open_positions, pending_orders
        )
        
        # Execute filtered entries
        self.order_executor.execute_entries(filtered_entries)
    
    def _suspend_trading_activity(self, market_state: dict) -> None:
        """
        Suspend all trading activity during news events.
        Cancels pending orders and optionally removes SL/TP from positions.
        
        Args:
            market_state: Current market state with positions and orders
        """
        self.logger.info("Suspending trading activity - storing and canceling orders/SL-TP")
        
        # Suspend pending orders
        self._suspend_pending_orders(market_state['pending_orders'])
        
        # Suspend SL/TP on positions (optional based on strategy)
        self._suspend_position_sl_tp(market_state['open_positions'])
        
        suspension_summary = self.suspension_store.get_summary()
        self.logger.info(f"Suspended {suspension_summary['total']} items: "
                        f"{suspension_summary['pending_order']} orders, "
                        f"{suspension_summary['position_sl_tp']} SL/TP")
    
    def _suspend_pending_orders(self, pending_orders: List[PendingOrder]) -> None:
        """
        Suspend all pending orders by storing their details and canceling them.
        
        Args:
            pending_orders: List of pending orders to suspend
        """
        for order in pending_orders:
            if order.symbol == self.config.SYMBOL:
                # Store order details for later restoration
                suspended_item: SuspendedItem = {
                    'ticket': order.ticket,
                    'kind': 'pending_order',
                    'original_sl': order.sl,
                    'original_tp': order.tp,
                    'symbol': order.symbol,
                    'order_type': self._get_order_type_name(order.type),
                    'volume': order.volume_current,
                    'price': order.price_open,
                    'magic': order.magic
                }
                
                self.suspension_store.add(suspended_item)
                
                # Cancel the order
                try:
                    result = self.trader.cancel_pending_orders(order.ticket)
                    if 'error' not in result:
                        self.logger.info(f"Canceled pending order {order.ticket}")
                    else:
                        self.logger.error(f"Failed to cancel pending order {order.ticket}: {result['error']}")
                except Exception as e:
                    self.logger.error(f"Error canceling order {order.ticket}: {e}")
    
    def _suspend_position_sl_tp(self, open_positions: List[Position]) -> None:
        """
        Suspend SL/TP on open positions by storing and removing them.
        
        Args:
            open_positions: List of open positions to process
        """
        for position in open_positions:
            if position.symbol == self.config.SYMBOL and (position.sl != 0 or position.tp != 0):
                # Store original SL/TP for restoration
                suspended_item: SuspendedItem = {
                    'ticket': position.ticket,
                    'kind': 'position_sl_tp',
                    'original_sl': position.sl if position.sl != 0 else None,
                    'original_tp': position.tp if position.tp != 0 else None,
                    'symbol': position.symbol,
                    'order_type': None,
                    'volume': None,
                    'price': None,
                    'magic': position.magic
                }
                
                self.suspension_store.add(suspended_item)
                
                # Remove SL/TP from position (use 0 to remove, not None)
                try:
                    result = self.trader.update_open_position(position.symbol, position.ticket, 0, 0)
                    if 'error' not in result:
                        self.logger.info(f"Removed SL/TP from position {position.ticket}")
                    else:
                        self.logger.error(f"Failed to remove SL/TP from position {position.ticket}: {result['error']}")
                except Exception as e:
                    self.logger.error(f"Error modifying position {position.ticket}: {e}")
    
    def _restore_suspended_activity(self) -> None:
        """
        Restore all suspended trading activity after news events end.
        Recreates pending orders and restores SL/TP on positions.
        """
        if self.suspension_store.is_empty():
            self.logger.info("No suspended items to restore")
            return
        
        suspended_items = self.suspension_store.all()
        self.logger.info(f"Restoring {len(suspended_items)} suspended items")
        
        # Restore pending orders
        pending_orders = self.suspension_store.get_by_kind('pending_order')
        for item in pending_orders:
            self._restore_pending_order(item)
        
        # Restore position SL/TP
        sl_tp_items = self.suspension_store.get_by_kind('position_sl_tp')
        for item in sl_tp_items:
            self._restore_position_sl_tp(item)
        
        # Clear the suspension store
        self.suspension_store.clear()
        self.logger.info("All suspended items restored and store cleared")
    
    def _restore_pending_order(self, item: SuspendedItem) -> None:
        """
        Restore a suspended pending order.
        
        Args:
            item: The suspended item containing order details
        """
        try:
            self.logger.info(
                f"Restoring pending order (original ticket: {item['ticket']}) "
                f"({item['order_type']}, {item['volume']}, {item['price']})"
            )
            
            # Recreate the order based on its type
            order_type = item['order_type']
            result = None
            
            if order_type == 'BUY_LIMIT':
                result = self.trader.client.orders.create_buy_limit_order(
                    symbol=item['symbol'],
                    volume=item['volume'],
                    price=item['price'],
                    stop_loss=item['original_sl'],
                    take_profit=item['original_tp'],
                    magic=item.get('magic')
                )
            elif order_type == 'SELL_LIMIT':
                result = self.trader.client.orders.create_sell_limit_order(
                    symbol=item['symbol'],
                    volume=item['volume'],
                    price=item['price'],
                    stop_loss=item['original_sl'],
                    take_profit=item['original_tp'],
                    magic=item.get('magic')
                )
            elif order_type == 'BUY_STOP':
                result = self.trader.client.orders.create_buy_stop_order(
                    symbol=item['symbol'],
                    volume=item['volume'],
                    price=item['price'],
                    stop_loss=item['original_sl'],
                    take_profit=item['original_tp'],
                    magic=item.get('magic')
                )
            elif order_type == 'SELL_STOP':
                result = self.trader.client.orders.create_sell_stop_order(
                    symbol=item['symbol'],
                    volume=item['volume'],
                    price=item['price'],
                    stop_loss=item['original_sl'],
                    take_profit=item['original_tp'],
                    magic=item.get('magic')
                )
            else:
                self.logger.warning(f"Unknown order type: {order_type}, cannot restore")
                return
            
            if result and isinstance(result, bool) and result:
                self.logger.info(f"Successfully restored order (was ticket {item['ticket']})")
            elif result and isinstance(result, dict) and 'error' not in result:
                self.logger.info(f"Successfully restored order (was ticket {item['ticket']})")
            else:
                error_msg = result.get('error', 'Unknown error') if isinstance(result, dict) else 'Failed'
                self.logger.error(f"Failed to restore order {item['ticket']}: {error_msg}")
                
        except Exception as e:
            self.logger.error(f"Error restoring pending order {item['ticket']}: {e}")
    
    def _restore_position_sl_tp(self, item: SuspendedItem) -> None:
        """
        Restore SL/TP on a suspended position.
        
        Args:
            item: The suspended item containing SL/TP details
        """
        try:
            result = self.trader.update_open_position(
                item['symbol'],
                item['ticket'], 
                item['original_sl'], 
                item['original_tp']
            )
            if 'error' not in result:
                self.logger.info(f"Restored SL/TP on position {item['ticket']}")
            else:
                self.logger.error(f"Failed to restore SL/TP on position {item['ticket']}: {result['error']}")
                
        except Exception as e:
            self.logger.error(f"Error restoring SL/TP on position {item['ticket']}: {e}")
    
    def _execute_daily_closure(self, market_state: dict) -> None:
        """
        Execute daily account closure - close all positions and cancel all orders.
        
        Args:
            market_state: Current market state with positions and orders
        """
        self.logger.info("Executing daily account closure")
        
        # Close all open positions
        for position in market_state['open_positions']:
            if position.symbol == self.config.SYMBOL:
                try:
                    result = self.trader.close_open_position(position.symbol, position.ticket)
                    if 'error' not in result:
                        self.logger.info(f"Closed position {position.ticket} for daily closure")
                    else:
                        self.logger.error(f"Failed to close position {position.ticket}: {result['error']}")
                except Exception as e:
                    self.logger.error(f"Error closing position {position.ticket}: {e}")
        
        # Cancel all pending orders
        for order in market_state['pending_orders']:
            if order.symbol == self.config.SYMBOL:
                try:
                    result = self.trader.cancel_pending_orders(order.ticket)
                    if 'error' not in result:
                        self.logger.info(f"Canceled pending order {order.ticket} for daily closure")
                    else:
                        self.logger.error(f"Failed to cancel pending order {order.ticket}: {result['error']}")
                except Exception as e:
                    self.logger.error(f"Error canceling order {order.ticket}: {e}")
        
        # Clear suspension store as we don't restore anything for daily closure
        if not self.suspension_store.is_empty():
            self.logger.info("Clearing suspension store for daily closure")
            self.suspension_store.clear()
    
    def _get_order_type_name(self, order_type: int) -> str:
        """
        Convert MT5 order type number to string name.
        
        Args:
            order_type: MT5 order type number
            
        Returns:
            String name of the order type
        """
        type_map = {
            0: 'BUY',
            1: 'SELL',
            2: 'BUY_LIMIT',
            3: 'SELL_LIMIT',
            4: 'BUY_STOP',
            5: 'SELL_STOP'
        }
        return type_map.get(order_type, f'UNKNOWN_{order_type}')
    
    def get_risk_metrics(self, date_helper: DateHelper) -> dict:
        """
        Get current risk metrics.
        
        Returns:
            Dictionary with current risk metrics
        """
        market_state = self._fetch_market_state(date_helper)
        
        return self.risk_monitor.get_risk_metrics(
            market_state['open_positions'],
            market_state['closed_positions']
        )