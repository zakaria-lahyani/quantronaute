"""
Order Executor - Handles order execution via trader.
"""

import logging
from typing import List

from ..live_trader import LiveTrader
from ..risk_manager.risk_calculator import RiskCalculator
from ..risk_manager.models import RiskEntryResult
from ...strategy_builder.data.dtos import EntryDecision


class OrderExecutor:
    """
    Executes orders through the trader interface.
    Single responsibility: Order execution.
    """
    
    def __init__(
        self, 
        trader: LiveTrader, 
        risk_calculator: RiskCalculator,
        symbol: str,
        logger: logging.Logger = None
    ):
        self.trader = trader
        self.risk_calculator = risk_calculator
        self.symbol = symbol
        self.logger = logger or logging.getLogger(self.__class__.__name__)
    
    def execute_entries(self, entries: List[EntryDecision]) -> None:
        """
        Execute entry orders.
        
        Args:
            entries: List of entry decisions to execute
        """
        if not entries:
            self.logger.debug("No entry signals to process")
            return
        
        current_price = self.trader.get_current_price(self.symbol)
        risk_entries = self.risk_calculator.process_entries(entries, current_price)
        
        for risk_entry in risk_entries:
            self._execute_risk_entry(risk_entry)
    
    def _execute_risk_entry(self, risk_entry: RiskEntryResult) -> None:
        """Execute a single risk entry group."""
        self.logger.info(f"Processing risk entry for group {risk_entry.group_id[:8]}")
        self.logger.info(f"Creating {len(risk_entry.limit_orders)} orders")
        
        try:
            # Open the orders and check results
            results = self.trader.open_pending_order(trade=risk_entry)
            
            # Process and log results
            self._process_execution_results(results, risk_entry)
            
        except Exception as e:
            self.logger.error(f"Failed to execute risk entry {risk_entry.group_id[:8]}: {e}")
    
    def _process_execution_results(
        self, 
        results: List, 
        risk_entry: RiskEntryResult
    ) -> None:
        """Process and log execution results."""
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
                if result:  # Assume non-None/non-empty responses are successful
                    success_count += 1
        
        total_orders = len(risk_entry.limit_orders)
        self.logger.info(
            f"Execution summary: {success_count}/{total_orders} orders successful "
            f"for group {risk_entry.group_id[:8]}"
        )