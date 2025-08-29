
import os
from collections import deque
from pathlib import Path
import time
import logging

from app.clients.mt5.client import create_client_with_retry
from app.data.data_manger import DataSourceManager
from app.entry_manager.manager import EntryManager
from app.indicators.indicator_processor import IndicatorProcessor
from app.strategy_builder.data.dtos import Trades, AllStrategiesEvaluationResult

from app.trader.executor_builder import ExecutorBuilder
from app.trader.trade_executor import TradeExecutor
from app.trader.trading_context import TradingContext

from app.utils.config import LoadEnvironmentVariables
from app.utils.functions_helper import has_new_candle
from app.utils.date_helper import DateHelper

from app.regime.regime_manager import RegimeManager
from app.main_backtest import load_strategies_configuration, load_indicator_configuration

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class LiveTradingManager:
    """
    Benefits of the new architecture:
    - Clean separation of concerns
    - Better error handling
    - Enhanced monitoring and logging
    - Easier to test and maintain
    """
    
    def __init__(self, config: LoadEnvironmentVariables):
        self.config = config
        self.candle_index = 2
        self.iteration_counter = 0
        self.consecutive_errors = 0
        self.max_consecutive_errors = 5
        
        # Initialize components
        self._initialize_components()
        
    def _initialize_components(self):
        """Initialize all trading components."""
        logger.info("Initializing live trading components...")
        
        # Create MT5 client
        self.client = create_client_with_retry(self.config.API_BASE_URL)
        
        # Strategy configuration
        engine = load_strategies_configuration(
            folder_path=self.config.CONF_FOLDER_PATH, 
            symbol=self.config.SYMBOL
        )
        self.strategies = {
            name: engine.get_strategy_info(name)
            for name in engine.list_available_strategies()
        }
        self.entry_manager = EntryManager(
            self.strategies, 
            symbol=self.config.SYMBOL, 
            pip_value=self.config.PIP_VALUE
        )
        self.strategy_engine = engine
        
        # Indicator configuration
        indicator_config = load_indicator_configuration(
            folder_path=self.config.CONF_FOLDER_PATH, 
            symbol=self.config.SYMBOL
        )
        
        # Timeframes and data management
        self.timeframes = list(indicator_config)
        self.last_known_bars = {tf: None for tf in self.timeframes}
        
        self.data_source = DataSourceManager(
            mode=self.config.TRADE_MODE, 
            client=self.client, 
            date_helper=DateHelper()
        )
        
        # Historical data
        historicals = {
            tf: self.data_source.get_historical_data(
                symbol=self.config.SYMBOL, 
                timeframe=tf
            ) 
            for tf in self.timeframes
        }
        
        # Indicators
        self.indicators = IndicatorProcessor(
            configs=indicator_config, 
            historicals=historicals, 
            is_bulk=False
        )
        
        # Regime detection
        self.regime_manager = RegimeManager(
            warmup_bars=500,
            persist_n=2,
            transition_bars=3,
            bb_threshold_len=200
        )
        self.regime_manager.setup(self.timeframes, historicals)
        
        self.trade_executor: TradeExecutor = ExecutorBuilder.build_from_config(
            config=self.config,
            client=self.client,
            logger=logging.getLogger('trade-executor')
        )
        
        # Account info
        self.account_balance = self.client.account.get_balance()
        
        logger.info("All components initialized successfully")
        logger.info(f"Trading {self.config.SYMBOL} with {len(self.timeframes)} timeframes")
        logger.info(f"Account balance: {self.account_balance}")
        
    def run(self):
        """Run the main trading loop."""
        logger.info("Starting live trading session...")
        
        try:
            while True:
                self._execute_trading_cycle()
                time.sleep(5)
                
        except KeyboardInterrupt:
            logger.info("Received keyboard interrupt. Shutting down gracefully...")
        except Exception as e:
            logger.error(f"Fatal error in main loop: {e}", exc_info=True)
        finally:
            self._cleanup()
            
    def _execute_trading_cycle(self):
        """Execute one complete trading cycle."""
        try:
            # Step 1: Fetch market data
            success_count = self._fetch_market_data()
            
            if success_count == 0:
                logger.warning("No data fetched from any timeframe this iteration")
                self.consecutive_errors += 1
                self._check_error_limit()
                return
                
            # Step 2: Evaluate strategies and generate trades
            self.iteration_counter += 1
            trades = self._evaluate_strategies()
            
            if trades is None:
                self.consecutive_errors += 1
                self._check_error_limit()
                return
                
            # Step 3: Execute trades using the new architecture
            context = self._execute_trades(trades)
            
            # Step 4: Log trading status
            self._log_trading_status(context, trades)
            
            # Reset error counter on successful cycle
            self.consecutive_errors = 0
            
        except Exception as e:
            logger.error(f"Error in trading cycle: {e}", exc_info=True)
            self.consecutive_errors += 1
            self._check_error_limit()
            
    def _fetch_market_data(self) -> int:
        """Fetch market data for all timeframes."""
        success_count = 0
        
        for tf in self.timeframes:
            try:
                df_stream = self.data_source.get_stream_data(
                    symbol=self.config.SYMBOL, 
                    timeframe=tf, 
                    nbr_bars=self.candle_index
                )
                success_count += 1
                
                if has_new_candle(df_stream, self.last_known_bars[tf], self.candle_index):
                    self.last_known_bars[tf] = df_stream.iloc[-self.candle_index]
                    
                    try:
                        # Update regime for this timeframe
                        regime_data = self.regime_manager.update(tf, df_stream.iloc[-self.candle_index])
                        
                        # Process indicators with regime data
                        self.indicators.process_new_row(tf, df_stream.iloc[-self.candle_index], regime_data)
                        
                        logger.debug(f"Updated {tf} data with regime: {regime_data}")
                        
                    except Exception as e:
                        logger.error(f"Error processing indicators for {tf}: {e}")
                        continue
                        
            except Exception as e:
                logger.warning(f"Error fetching stream data for {tf}: {e}")
                continue
                
        return success_count
        
    def _evaluate_strategies(self) -> Trades:
        """Evaluate strategies and generate trade signals."""
        try:
            # Get recent rows from indicators (enriched with regime data)
            recent_rows: dict[str, deque] = self.indicators.get_recent_rows()
            
            # Evaluate strategies
            strategy_result: AllStrategiesEvaluationResult = self.strategy_engine.evaluate(recent_rows)
            
            # Generate trades
            trades: Trades = self.entry_manager.manage_trades(
                strategy_result.strategies, 
                recent_rows, 
                self.account_balance
            )
            
            logger.debug(f"Generated {len(trades.entries)} entries, {len(trades.exits)} exits")
            return trades
            
        except Exception as e:
            logger.error(f"Error in strategy evaluation: {e}", exc_info=True)
            return None
            
    def _execute_trades(self, trades: Trades) -> TradingContext:
        """Execute trades using the new TradeExecutor architecture."""
        logger.debug(f"Executing trades: {len(trades.entries)} entries, {len(trades.exits)} exits")
        
        # Execute trading cycle with the new architecture
        context = self.trade_executor.execute_trading_cycle(trades, DateHelper())
        
        return context
        
    def _log_trading_status(self, context: TradingContext, trades: Trades):
        """Log detailed trading status information."""
        # Basic iteration info
        if self.iteration_counter % 100 == 0:  # Log every 100 iterations
            logger.info(f"Iteration {self.iteration_counter} completed")
            
        # Log trades if any
        if trades.entries or trades.exits:
            logger.info(f"Trades - Entries: {len(trades.entries)}, Exits: {len(trades.exits)}")
            
        # Log important context changes
        if not context.trade_authorized:
            logger.warning(f"Trading blocked - News: {context.news_block_active}, Market closing: {context.market_closing_soon}")
            
        if context.risk_breached:
            logger.warning(f"Risk limit breached! Total P&L: {context.total_pnl}")
            
        # Log market state summary
        if context.market_state:
            state = context.market_state
            if state.has_open_positions or state.has_pending_orders:
                logger.info(
                    f"Positions: {len(state.open_positions)}, "
                    f"Orders: {len(state.pending_orders)}, "
                    f"P&L: {context.daily_pnl:.2f}"
                )
                
    def _check_error_limit(self):
        """Check if we've exceeded the maximum consecutive errors."""
        if self.consecutive_errors >= self.max_consecutive_errors:
            logger.error(
                f"Too many consecutive errors ({self.consecutive_errors}). Exiting..."
            )
            raise SystemExit(1)
            
    def _cleanup(self):
        """Cleanup resources before shutdown."""
        logger.info("🧹 Cleaning up resources...")
        
        try:
            # Get final context for logging
            final_context = self.trade_executor.get_context()
            
            if final_context.market_state:
                state = final_context.market_state
                logger.info(
                    f"Final state - Positions: {len(state.open_positions)}, "
                    f"Orders: {len(state.pending_orders)}, "
                    f"Daily P&L: {final_context.daily_pnl:.2f}"
                )
                
        except Exception as e:
            logger.error(f"Error getting final state: {e}")
            
        logger.info("Shutdown complete")


def main():
    """Main entry point - Updated to use the new architecture."""
    # Load configuration
    ROOT_DIR = Path(__file__).parent.parent
    config = LoadEnvironmentVariables(os.path.join(ROOT_DIR, ".env"))
    
    # Create and run the trading manager
    trading_manager = LiveTradingManager(config)
    trading_manager.run()


if __name__ == "__main__":
    import sys

    main()
