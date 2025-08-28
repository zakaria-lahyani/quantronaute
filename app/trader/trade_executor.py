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
    
    def manage(self, trades: Trades, date_helper: DateHelper) -> None:
        """
        Main orchestration method - coordinates all components.
        
        Args:
            trades: Trade signals to process
            date_helper: Date helper for time calculations
        """
        self.logger.info("=== TRADE EXECUTION CYCLE START ===")
        
        try:
            # 1. Fetch current market state
            market_state = self._fetch_market_state(date_helper)
            
            # 2. Process exits first
            self._process_exits(trades.exits, market_state['open_positions'])
            
            # 3. Check risk limits
            risk_breached = self._check_risk_limits(
                market_state['open_positions'], 
                market_state['closed_positions']
            )
            
            # 4. Process entries only if risk is acceptable
            if not risk_breached:
                self._process_entries(
                    trades.entries, 
                    market_state['open_positions'], 
                    market_state['pending_orders']
                )
            else:
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
        
        # Filter duplicates
        filtered_entries = self.duplicate_filter.filter_entries(
            entries, open_positions, pending_orders
        )
        
        # Execute filtered entries
        self.order_executor.execute_entries(filtered_entries)
    
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