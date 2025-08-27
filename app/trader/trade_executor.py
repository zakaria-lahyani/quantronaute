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

        # self.trade_restriction = TradeRestriction(
        #     restriction_path=config.RESTRICTION_CONF_FOLDER_PATH,
        #     default_close_time_str=config.DEFAULT_CLOSE_TIME,
        #     news_duration=config.NEWS_RESTRICTION_DURATION,
        #     market_close_duration=config.MARKET_CLOSE_RESTRICTION_DURATION
        # )

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
        # is_trade_allow = self._check_schedule()
        # if (is_trade_allow):
        self.exec_open_pending_orders(entries)


