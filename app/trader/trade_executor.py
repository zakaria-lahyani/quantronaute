import logging
from datetime import datetime

from app.clients.mt5.models.history import ClosedPosition
from app.clients.mt5.models.order import PendingOrder
from app.clients.mt5.models.response import Position
from app.strategy_builder.data.dtos import Trades, EntryDecision, ExitDecision
from app.trader.live_trader import LiveTrader
from app.trader.risk_manager.models import ScalingConfig, RiskEntryResult
from app.trader.risk_manager.risk_calculator import RiskCalculator
from app.trader.trade_restriction import TradeRestriction
from app.utils.config import LoadEnvironmentVariables
from app.utils.date_helper import DateHelper


class TradeExecutor:
    def __init__(self, mode: str, config:LoadEnvironmentVariables, **kwargs):
        self.mode = mode
        self.TRADER_IS_UP = True
        self.logger = logging.getLogger('trade-executor')
        self.config = config

        self.scaling_config = ScalingConfig(
            num_entries=config.POSITION_SPLIT,
            scaling_type=config.SCALING_TYPE,
            entry_spacing=config.ENTRY_SPACING,
            max_risk_per_group=config.RISK_PER_GROUP
        )
        self.risk_calculator = RiskCalculator(self.scaling_config)

        if mode == 'live':
            if 'client' not in kwargs:
                raise ValueError("Live trading requires client")
            self.trader = LiveTrader(kwargs['client'])

    def manage_exits(self, exits: list[ExitDecision], open_positions: list[Position]):
        for exit_trade in exits:
            exit_type = 0 if exit_trade.direction == "long" else 1
            magic = exit_trade.magic
            symbol = exit_trade.symbol
            for opened_trade in open_positions:
                if opened_trade.symbol == symbol and opened_trade.magic == magic and opened_trade.type == exit_type:
                    self.trader.close_open_position(symbol, opened_trade.ticket)

    def _check_catastrophic_loss_limit(
            self, opened: list[Position], closed_positions: list[ClosedPosition] ):

        closed_pnl = self.calculate_close_pnl(closed_positions)
        floating_pnl = self.calculate_floating_pnl(opened)
        total_pnl_today = closed_pnl + floating_pnl

        loss_ratio = total_pnl_today / self.config.DAILY_LOSS_LIMIT

        print(loss_ratio)
        if loss_ratio < -1 :
            self.trader.close_all_open_position()
            self.trader.cancel_all_pending_orders()
            # self.TRADER_IS_UP = False

    def filter_duplicate_entries(
        self, 
        entries: list[EntryDecision], 
        open_positions: list[Position], 
        pending_orders: list[PendingOrder]
    ) -> list[EntryDecision]:
        """
        Filter out entry signals that would create duplicate trades.
        Checks both open positions and pending orders for matching magic number and type.
        
        Args:
            entries: List of entry decisions to filter
            open_positions: Currently open positions
            pending_orders: Currently pending orders
            
        Returns:
            Filtered list of entry decisions without duplicates
        """
        if not entries:
            return entries
        
        filtered_entries = []
        
        # Debug logging
        self.logger.info(f"=== DUPLICATE FILTER START ===")
        self.logger.info(f"Checking {len(entries)} entries for duplicates")
        self.logger.info(f"Current open positions: {len(open_positions)}")
        self.logger.info(f"Current pending orders: {len(pending_orders)}")
        
        # Create sets of existing trades for quick lookup
        # Format: (magic, type) where type is 0 for buy/long, 1 for sell/short
        existing_positions = {
            (pos.magic, pos.type) 
            for pos in open_positions
        }
        
        existing_pending = {
            (order.magic, order.type) 
            for order in pending_orders
        }
        
        # Debug: Show existing trades
        if existing_positions:
            self.logger.info(f"Existing positions (magic, type): {existing_positions}")
        if existing_pending:
            self.logger.info(f"Existing pending (magic, type): {existing_pending}")
        
        # Combine both sets
        existing_trades = existing_positions | existing_pending
        
        for entry in entries:
            # Convert entry signal to MT5 order type
            # 0=BUY, 1=SELL, 2=BUY_LIMIT, 3=SELL_LIMIT
            type_map = {
                'BUY': 0,
                'SELL': 1,
                'BUY_LIMIT': 2,
                'SELL_LIMIT': 3
            }
            entry_type = type_map.get(entry.entry_signals, -1)
            
            if entry_type == -1:
                self.logger.error(f"Unknown entry signal type: {entry.entry_signals}")
                continue
                
            trade_key = (entry.magic, entry_type)
            
            self.logger.info(f"Checking entry: magic={entry.magic}, type={entry_type}, signal={entry.entry_signals}")
            
            if trade_key not in existing_trades:
                filtered_entries.append(entry)
                self.logger.info(
                    f"Entry ALLOWED: {entry.strategy_name} {entry.direction} "
                    f"(magic={entry.magic}, type={entry_type})"
                )
            else:
                self.logger.warning(
                    f"Entry BLOCKED (duplicate): {entry.strategy_name} {entry.direction} "
                    f"(magic={entry.magic}, type={entry_type}) - "
                    f"Already exists in {'positions' if trade_key in existing_positions else 'pending orders'}"
                )
        
        initial_count = len(entries)
        filtered_count = len(filtered_entries)
        
        self.logger.info(
            f"=== FILTER RESULT: {filtered_count}/{initial_count} entries passed "
            f"({initial_count - filtered_count} duplicates removed) ==="
        )
        
        return filtered_entries
    
    def exec_open_pending_orders(self, entries: list[EntryDecision]):
        current_price = self.trader.get_current_price(self.config.SYMBOL)

        if not entries:
            self.logger.debug("No entry signals to process")
            return

        risk_entries: list[RiskEntryResult] = self.risk_calculator.process_entries(entries, current_price)

        for risk_entry in risk_entries:
            self.logger.info(f"Processing risk entry for group {risk_entry.group_id[:8]}")
            self.logger.info(f"Creating {len(risk_entry.limit_orders)} orders")

            # Open the orders and check results
            results = self.trader.open_pending_order(trade=risk_entry)

            # Log the results
            success_count = 0
            for i, result in enumerate(results):
                if isinstance(result, dict):
                    if 'error' in result:
                        self.logger.error(f"Order {i + 1} failed: {result['error']}")
                    else:
                        self.logger.info(f"Order {i + 1} result: {result}")
                        if result.get('status') == 'success' or result.get('result'):
                            success_count += 1
                else:
                    self.logger.info(f"Order {i + 1} response: {result}")

            self.logger.info(f"Successfully created {success_count}/{len(risk_entry.limit_orders)} orders")

    def calculate_close_pnl(self, closed_positions: list[ClosedPosition]):
        if not closed_positions:
            return 0
        else:
            profit = sum(pos.profit for pos in closed_positions)
            commissions = sum(pos.commission for pos in closed_positions)
            swaps = sum(pos.swap for pos in closed_positions)
            return profit + commissions + swaps

    def calculate_floating_pnl(self, opened: list[Position]):
        if not opened:
            return 0
        else:
            profit = sum(pos.profit for pos in opened)
            swaps = sum(pos.swap for pos in opened)
            return profit + swaps


    def manage(self, trades: Trades, date_helper: DateHelper):
        start_date = f"{date_helper.get_date_days_ago(0)}T00:00:00Z"
        end_date = f"{date_helper.get_date_days_ago(-1)}T00:00:00Z"

        entries: list[EntryDecision] = trades.entries
        exits: list[ExitDecision] = trades.exits

        closed_positions = self.trader.get_closed_positions(start_date, end_date)
        pending_orders: list[PendingOrder] = self.trader.get_pending_orders(self.config.SYMBOL)
        open_positions: list[Position] = self.trader.get_open_positions(self.config.SYMBOL)

        current_time = datetime.now().astimezone()

        self.manage_exits(exits, open_positions)
        self._check_catastrophic_loss_limit(open_positions, closed_positions)
        
        # Filter out duplicate entries before execution
        filtered_entries = self.filter_duplicate_entries(entries, open_positions, pending_orders)
        
        # is_trade_allow = self._check_schedule()
        # if (is_trade_allow):
        self.exec_open_pending_orders(filtered_entries)


