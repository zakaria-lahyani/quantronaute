from typing import Optional, List, Dict, Any
import logging

from app.clients.mt5.client import MT5Client
from app.clients.mt5.models.history import ClosedPosition
from app.clients.mt5.models.order import PendingOrder
from app.clients.mt5.models.position import Position

from app.trader.base_trader import BaseTrader
from app.trader.risk_manager.models import RiskEntryResult


class LiveTrader(BaseTrader):
    def __init__(self, client: MT5Client, logger: Optional[logging.Logger] = None):
        """
        Initialize LiveTrader with MT5 API clients.

        Args:
            client: MT5Client instance for trading operations
            logger: Optional logger for debugging
        """
        super().__init__()
        self.client = client
        self.logger = logger or logging.getLogger(self.__class__.__name__)

    def get_current_price(self, symbol:str):
        price = self.client.symbols.get_symbol_price(symbol)
        return price["bid"]

    def open_pending_order(self, trade: RiskEntryResult) -> List[Dict[str, Any]]:
        """
        Open multiple pending orders from a RiskEntryResult.
        
        Args:
            trade: RiskEntryResult containing multiple limit orders
            
        Returns:
            List of responses from order creation
        """
        results = []
        
        for order in trade.limit_orders:
            try:
                # Determine order creation method based on order type
                if order['order_type'] == 'BUY_LIMIT':
                    result = self.client.orders.create_buy_limit_order(
                        symbol=order['symbol'],
                        volume=order['volume'],
                        price=order['price'],
                        stop_loss=order.get('group_stop_loss'),  # Use group stop loss
                        take_profit=trade.take_profit.level if trade.take_profit else None,
                        comment=f"Group_{trade.group_id[:8]}",
                        magic=0  # You may want to generate this from strategy
                    )
                elif order['order_type'] == 'SELL_LIMIT':
                    result = self.client.orders.create_sell_limit_order(
                        symbol=order['symbol'],
                        volume=order['volume'],
                        price=order['price'],
                        stop_loss=order.get('group_stop_loss'),  # Use group stop loss
                        take_profit=trade.take_profit.level if trade.take_profit else None,
                        comment=f"Group_{trade.group_id[:8]}",
                        magic=0  # You may want to generate this from strategy
                    )
                elif order['order_type'] == 'BUY_STOP':
                    result = self.client.orders.create_buy_stop_order(
                        symbol=order['symbol'],
                        volume=order['volume'],
                        price=order['price'],
                        stop_loss=order.get('group_stop_loss'),
                        take_profit=trade.take_profit.level if trade.take_profit else None,
                        comment=f"Group_{trade.group_id[:8]}",
                        magic=0
                    )
                elif order['order_type'] == 'SELL_STOP':
                    result = self.client.orders.create_sell_stop_order(
                        symbol=order['symbol'],
                        volume=order['volume'],
                        price=order['price'],
                        stop_loss=order.get('group_stop_loss'),
                        take_profit=trade.take_profit.level if trade.take_profit else None,
                        comment=f"Group_{trade.group_id[:8]}",
                        magic=0
                    )
                else:
                    self.logger.warning(f"Unknown order type: {order['order_type']}")
                    continue
                    
                results.append(result)
                self.logger.info(
                    f"Created {order['order_type']} order for {order['symbol']} "
                    f"at {order['price']} with volume {order['volume']}"
                )
                
            except Exception as e:
                self.logger.error(f"Failed to create order: {e}")
                results.append({"error": str(e), "order": order})
                
        return results

    def get_pending_orders(self, symbol: Optional[str] = None) -> List[PendingOrder]:
        """
        Get all pending orders, optionally filtered by symbol.
        
        Args:
            symbol: Optional symbol to filter orders
            
        Returns:
            List of pending orders
        """
        try:
            orders = self.client.orders.get_pending_orders(symbol)
            self.logger.debug(f"Retrieved {len(orders)} pending orders")
            return orders
        except Exception as e:
            self.logger.error(f"Failed to get pending orders: {e}")
            return []

    def update_pending_orders(
        self, 
        ticket: int, 
        price: Optional[float] = None, 
        sl: Optional[float] = None, 
        tp: Optional[float] = None,
        comment: str = ""
    ) -> Dict[str, Any]:
        """
        Update a pending order's parameters.
        
        Args:
            ticket: Order ticket ID
            price: New price level
            sl: New stop loss
            tp: New take profit
            comment: New comment
            
        Returns:
            Response from the update operation
        """
        try:
            result = self.client.orders.update_pending_order(
                ticket=ticket,
                price=price,
                stop_loss=sl,
                take_profit=tp,
                comment=comment
            )
            self.logger.info(f"Updated pending order {ticket}")
            return result
        except Exception as e:
            self.logger.error(f"Failed to update pending order {ticket}: {e}")
            return {"error": str(e)}

    def cancel_pending_orders(self, ticket: int) -> Dict[str, Any]:
        """
        Cancel a specific pending order.
        
        Args:
            ticket: Order ticket ID to cancel
            
        Returns:
            Response from the cancellation
        """
        try:
            result = self.client.orders.delete_pending_order(ticket)
            self.logger.info(f"Cancelled pending order {ticket}")
            return result
        except Exception as e:
            self.logger.error(f"Failed to cancel pending order {ticket}: {e}")
            return {"error": str(e)}

    def cancel_all_pending_orders(self, symbol: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Cancel all pending orders, optionally filtered by symbol.
        
        Args:
            symbol: Optional symbol to filter orders to cancel
            
        Returns:
            List of cancellation results
        """
        results = []
        try:
            orders = self.get_pending_orders(symbol)
            for order in orders:
                result = self.cancel_pending_orders(order.ticket)
                results.append(result)
            
            self.logger.info(f"Cancelled {len(results)} pending orders")
            return results
        except Exception as e:
            self.logger.error(f"Failed to cancel all pending orders: {e}")
            return [{"error": str(e)}]

    def get_open_positions(self, symbol: Optional[str] = None) -> List[Position]:
        """
        Get all open positions, optionally filtered by symbol.
        
        Args:
            symbol: Optional symbol to filter positions
            
        Returns:
            List of open positions
        """
        try:
            if symbol:
                positions = self.client.positions.get_positions_by_symbol(symbol)
            else:
                positions = self.client.positions.get_open_positions()
            
            self.logger.debug(f"Retrieved {len(positions)} open positions")
            return positions
        except Exception as e:
            self.logger.error(f"Failed to get open positions: {e}")
            return []

    def update_open_position(
        self, 
        symbol: str, 
        ticket: int, 
        sl: Optional[float] = None, 
        tp: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Update stop loss or take profit of an open position.
        
        Args:
            symbol: Trading symbol
            ticket: Position ticket ID
            sl: New stop loss level
            tp: New take profit level
            
        Returns:
            Response from the update operation
        """
        try:
            result = self.client.positions.modify_position(
                symbol=symbol,
                ticket=ticket,
                stop_loss=sl,
                take_profit=tp
            )
            self.logger.info(f"Updated position {ticket} for {symbol}")
            return result
        except Exception as e:
            self.logger.error(f"Failed to update position {ticket}: {e}")
            return {"error": str(e)}

    def close_open_position(
        self, 
        symbol: str, 
        ticket: int, 
        volume: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Close a specific open position.
        
        Args:
            symbol: Trading symbol
            ticket: Position ticket ID
            volume: Volume to close (if None, closes entire position)
            
        Returns:
            Response from the close operation
        """
        try:
            # If volume not specified, get the position to close full volume
            if volume is None:
                position = self.client.positions.get_position_by_ticket(ticket)
                if position:
                    volume = position.volume
                else:
                    return {"error": f"Position {ticket} not found"}
            
            result = self.client.positions.close_position(
                symbol=symbol,
                ticket=ticket,
                volume=volume
            )
            self.logger.info(f"Closed position {ticket} for {symbol}")
            return result
        except Exception as e:
            self.logger.error(f"Failed to close position {ticket}: {e}")
            return {"error": str(e)}

    def close_all_open_position(self) -> Dict[str, Any]:
        """
        Close all open positions.
        
        Returns:
            Response from the close all operation
        """
        try:
            result = self.client.positions.close_all_positions()
            self.logger.info("Closed all positions")
            return result
        except Exception as e:
            self.logger.error(f"Failed to close all positions: {e}")
            return {"error": str(e)}

    def get_closed_positions(self, start: str, end: str) -> List[ClosedPosition]:
        """
        Get historical closed positions within a date range.
        
        Args:
            start: Start date (format: 'YYYY-MM-DD')
            end: End date (format: 'YYYY-MM-DD')
            
        Returns:
            List of closed positions
        """
        try:
            # Assuming there's a history client in MT5Client
            positions = self.client.history.get_closed_positions(start, end)
            self.logger.debug(
                f"Retrieved {len(positions)} closed positions from {start} to {end}"
            )
            return positions
        except Exception as e:
            self.logger.error(f"Failed to get closed positions: {e}")
            return []

    def manage_group_stop_loss(self, group_id: str, positions: List[Position]) -> None:
        """
        Manage stop loss for a group of related positions.
        
        This is a helper method to update stop losses for positions
        that are part of the same scaling group.
        
        Args:
            group_id: The group identifier
            positions: List of positions in the group
        """
        # This would be implemented based on your specific group management logic
        pass

    def get_account_info(self) -> Dict[str, Any]:
        """
        Get current account information.
        
        Returns:
            Account information including balance, equity, margin, etc.
        """
        try:
            info = self.client.account.get_account_info()
            return info
        except Exception as e:
            self.logger.error(f"Failed to get account info: {e}")
            return {}