from typing import Optional

from app.clients.mt5.client import MT5Client
from app.clients.mt5.models.history import ClosedPosition
from app.clients.mt5.models.order import PendingOrder
from app.clients.mt5.models.position import Position
from app.strategy_builder.data.dtos import EntryDecision
from app.trader.base_trader import BaseTrader


class LiveTrader(BaseTrader):
    def __init__(self, client: MT5Client):
        """
        Initialize LiveTrader with MT5 API clients.

        Args:
            endpoints (Mt5Endpoints): A container holding clients for order, position,
                                      account, and historical trade operations.
        """
        super()
        self.client = client

    def open_pending_order(self, trade: EntryDecision):
        # self.client.orders.create_buy_limit_order(
        #     symbol=trade.symbol,
        #     volume=trade.position_size,
        #     price=trade.entry_price,
        #     stop_loss=trade.,
        #     take_profit=trade.take_profit,
        #     comment=trade.comment,
        #     magic=trade.magic,
        # )
        pass

    def get_pending_orders(self, symbol: Optional[str] = None) -> list[PendingOrder]:
        pass

    def update_pending_orders(self, ticket: int, price: float = None, sl: float = None, tp: float = None,
                              comment: str = ""):
        pass

    def cancel_pending_orders(self, ticket: int):
        pass

    def cancel_all_pending_orders(self, symbol: Optional[str] = None):
        pass

    def get_open_positions(self, symbol: Optional[str] = None) -> list[Position]:
        pass

    def update_open_position(self, symbol: str, ticket: int, sl: Optional[float] = None, tp: Optional[float] = None):
        pass

    def close_open_position(self, symbol: str, ticket: int, volume: float = None):
        pass

    def close_all_open_position(self):
        pass

    def get_closed_positions(self, start: str, end: str) -> list[ClosedPosition]:
        pass