"""
Duplicate Filter - Prevents duplicate trade entries.
"""

import logging
from typing import List, Set, Tuple

from ...clients.mt5.models.response import Position
from ...clients.mt5.models.order import PendingOrder
from ...strategy_builder.data.dtos import EntryDecision


class DuplicateFilter:
    """
    Filters duplicate entry signals to prevent redundant trades.
    Single responsibility: Duplicate detection and filtering.
    """
    
    def __init__(self, logger: logging.Logger = None):
        self.logger = logger or logging.getLogger(self.__class__.__name__)
    
    def filter_entries(
        self, 
        entries: List[EntryDecision], 
        open_positions: List[Position], 
        pending_orders: List[PendingOrder]
    ) -> List[EntryDecision]:
        """
        Filter out entry signals that would create duplicate trades.
        
        Args:
            entries: List of entry decisions to filter
            open_positions: Currently open positions
            pending_orders: Currently pending orders
            
        Returns:
            Filtered list of entry decisions without duplicates
        """
        if not entries:
            return entries
        
        self.logger.info(f"=== DUPLICATE FILTER START ===")
        self.logger.info(f"Checking {len(entries)} entries for duplicates")
        self.logger.info(f"Current open positions: {len(open_positions)}")
        self.logger.info(f"Current pending orders: {len(pending_orders)}")
        
        existing_trades = self._get_existing_trades(open_positions, pending_orders)
        filtered_entries = self._filter_against_existing(entries, existing_trades, open_positions, pending_orders)
        
        initial_count = len(entries)
        filtered_count = len(filtered_entries)
        
        self.logger.info(
            f"=== FILTER RESULT: {filtered_count}/{initial_count} entries passed "
            f"({initial_count - filtered_count} duplicates removed) ==="
        )
        
        return filtered_entries
    
    def _get_existing_trades(
        self, 
        open_positions: List[Position], 
        pending_orders: List[PendingOrder]
    ) -> Set[Tuple[int, int]]:
        """Get set of existing trades as (magic, type) tuples."""
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
        
        return existing_positions | existing_pending
    
    def _filter_against_existing(
        self, 
        entries: List[EntryDecision], 
        existing_trades: Set[Tuple[int, int]],
        existing_positions: Set[Tuple[int, int]],
        existing_pending: Set[Tuple[int, int]]
    ) -> List[EntryDecision]:
        """Filter entries against existing trades."""
        filtered_entries = []
        
        for entry in entries:
            entry_type = self._get_order_type(entry.entry_signals)
            
            if entry_type == -1:
                self.logger.error(f"Unknown entry signal type: {entry.entry_signals}")
                continue
                
            trade_key = (entry.magic, entry_type)
            
            self.logger.info(f"Checking entry: magic={entry.magic}, type={entry_type}, signal={entry.entry_signals}")
            
            if trade_key not in existing_trades:
                filtered_entries.append(entry)
                self.logger.info(
                    f"✅ Entry ALLOWED: {entry.strategy_name} {entry.direction} "
                    f"(magic={entry.magic}, type={entry_type})"
                )
            else:
                source = "positions" if trade_key in existing_positions else "pending orders"
                self.logger.warning(
                    f"❌ Entry BLOCKED (duplicate): {entry.strategy_name} {entry.direction} "
                    f"(magic={entry.magic}, type={entry_type}) - Already exists in {source}"
                )
        
        return filtered_entries
    
    def _get_order_type(self, entry_signal: str) -> int:
        """Convert entry signal to MT5 order type."""
        type_map = {
            'BUY': 0,
            'SELL': 1,
            'BUY_LIMIT': 2,
            'SELL_LIMIT': 3
        }
        return type_map.get(entry_signal, -1)