import logging

from app.clients.mt5.models.response import Position
from app.strategy_builder.data.dtos import Trades, EntryDecision, ExitDecision
from app.trader.live_trader import LiveTrader
from app.trader.risk_manager.models import ScalingConfig, RiskEntryResult
from app.trader.risk_manager.risk_calculator import RiskCalculator
from app.utils.config import LoadEnvironmentVariables


class TradeExecutor:
    def __init__(self, mode: str, config:LoadEnvironmentVariables, **kwargs):
        self.mode = mode
        self.DAILY_LOSS_LIMIT = config.DAILY_LOSS_LIMIT
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


    def manage(self, trades: Trades):
        entries: list[EntryDecision] = trades.entries
        exits: list[ExitDecision] = trades.exits

        print(entries)
        print(exits)

        self.exec_open_pending_orders(entries)

        closed_positions = self.trader.get_closed_positions("2025-08-22", "2025-08-24")
        pending_orders = self.trader.get_pending_orders(self.config.SYMBOL)
        open_positions = self.trader.get_open_positions(self.config.SYMBOL)

        print( pending_orders )
        print( open_positions )
        print( closed_positions )


        # print(self.open_pending_p(entries) )

            # # Check pending orders
            # pending = self.trader.get_pending_orders(risk_entry.limit_orders[0]['symbol'])
            # self.logger.info(f"Current pending orders for {risk_entry.limit_orders[0]['symbol']}: {len(pending)} orders")

        # for trade in trades.entries:
        #     risk_entries: RiskEntryResult = self.risk_calculator.process_entry_signal(trade, current_price)
        #     print(risk_entries)
