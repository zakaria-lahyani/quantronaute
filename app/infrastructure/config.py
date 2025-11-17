"""
Configuration models and loader for the trading system.

This module provides Pydantic models for validating configuration
and a loader that reads from YAML files with environment variable overrides.
"""

import os
import logging
from typing import List, Optional, Dict, Any, Literal
from pathlib import Path

from pydantic import BaseModel, Field, field_validator
import yaml


class DataFetchingConfig(BaseModel):
    """Configuration for DataFetchingService."""

    enabled: bool = True
    fetch_interval: int = Field(default=5, ge=1, le=60)
    retry_attempts: int = Field(default=3, ge=0, le=10)
    candle_index: int = Field(default=1, ge=1)
    nbr_bars: int = Field(default=3, ge=1)


class IndicatorCalculationConfig(BaseModel):
    """Configuration for IndicatorCalculationService."""

    enabled: bool = True
    recent_rows_limit: int = Field(default=6, ge=1)
    track_regime_changes: bool = True


class StrategyEvaluationConfig(BaseModel):
    """Configuration for StrategyEvaluationService."""

    enabled: bool = True
    evaluation_mode: Literal["on_new_candle", "continuous"] = "on_new_candle"
    min_rows_required: int = Field(default=3, ge=1)


class TradeExecutionConfig(BaseModel):
    """Configuration for TradeExecutionService."""

    enabled: bool = True
    execution_mode: Literal["immediate", "batch"] = "immediate"
    batch_size: int = Field(default=1, ge=1)


class ServicesConfig(BaseModel):
    """Configuration for all services."""

    data_fetching: DataFetchingConfig = Field(default_factory=DataFetchingConfig)
    indicator_calculation: IndicatorCalculationConfig = Field(
        default_factory=IndicatorCalculationConfig
    )
    strategy_evaluation: StrategyEvaluationConfig = Field(
        default_factory=StrategyEvaluationConfig
    )
    trade_execution: TradeExecutionConfig = Field(
        default_factory=TradeExecutionConfig
    )


class EventBusConfig(BaseModel):
    """Configuration for EventBus."""

    mode: Literal["synchronous", "asynchronous"] = "synchronous"
    event_history_limit: int = Field(default=1000, ge=0)
    log_all_events: bool = False


class OrchestratorConfig(BaseModel):
    """Configuration for TradingOrchestrator."""

    enable_auto_restart: bool = True
    health_check_interval: int = Field(default=60, ge=10)
    status_log_interval: int = Field(default=10, ge=1)


class LoggingConfig(BaseModel):
    """Configuration for logging."""

    level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    format: Literal["json", "text"] = "text"
    correlation_ids: bool = True
    file_output: bool = False
    log_file: str = "logs/trading_system.log"


class TradingConfig(BaseModel):
    """Configuration for trading parameters."""

    symbols: List[str] = Field(min_length=1)
    timeframes: List[str] = Field(min_length=1)

    @field_validator("symbols")
    @classmethod
    def validate_symbols(cls, v: List[str]) -> List[str]:
        """Validate symbols are not empty."""
        if not v:
            raise ValueError("At least one symbol must be specified")
        return [s.upper() for s in v]  # Normalize to uppercase

    @field_validator("timeframes")
    @classmethod
    def validate_timeframes(cls, v: List[str]) -> List[str]:
        """Validate timeframes are not empty."""
        if not v:
            raise ValueError("At least one timeframe must be specified")
        return v


class AccountStopLossConfig(BaseModel):
    """Configuration for account-level stop loss."""

    enabled: bool = True
    daily_loss_limit: float = Field(default=1000.0, ge=0)
    max_drawdown_pct: float = Field(default=10.0, ge=0, le=100)
    close_positions_on_breach: bool = True
    stop_trading_on_breach: bool = True
    cooldown_period_minutes: int = Field(default=60, ge=0)
    daily_reset_time: str = "00:00:00"
    timezone_offset: str = "+00:00"


class RiskConfig(BaseModel):
    """Configuration for risk management."""

    daily_loss_limit: float = Field(default=1000.0, ge=0)  # Legacy - use account_stop_loss.daily_loss_limit
    max_positions: int = Field(default=10, ge=1)
    max_position_size: float = Field(default=1.0, ge=0.01)
    account_stop_loss: AccountStopLossConfig = Field(default_factory=AccountStopLossConfig)


class AutomationConfig(BaseModel):
    """Configuration for automated trading control."""

    enabled: bool = True
    state_file: str = "config/automation_state.json"
    toggle_file: str = "config/toggle_automation.txt"
    file_watcher_enabled: bool = True
    file_watcher_interval: int = Field(default=5, ge=1, le=60)

    @field_validator("enabled", mode="before")
    @classmethod
    def parse_bool(cls, v: Any) -> bool:
        """Parse boolean from various string formats."""
        if isinstance(v, bool):
            return v
        if isinstance(v, str):
            return v.lower() in ("true", "1", "yes", "on")
        return bool(v)


class SystemConfig(BaseModel):
    """Complete system configuration."""

    services: ServicesConfig = Field(default_factory=ServicesConfig)
    event_bus: EventBusConfig = Field(default_factory=EventBusConfig)
    orchestrator: OrchestratorConfig = Field(default_factory=OrchestratorConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    trading: TradingConfig
    risk: RiskConfig = Field(default_factory=RiskConfig)
    automation: AutomationConfig = Field(default_factory=AutomationConfig)

    def to_orchestrator_config(self) -> Dict[str, Any]:
        """
        Convert to orchestrator configuration dictionary.

        Returns:
            Dictionary suitable for TradingOrchestrator initialization
        """
        return {
            "symbols": self.trading.symbols,
            "timeframes": self.trading.timeframes,
            "enable_auto_restart": self.orchestrator.enable_auto_restart,
            "health_check_interval": self.orchestrator.health_check_interval,
            "event_history_limit": self.event_bus.event_history_limit,
            "log_all_events": self.event_bus.log_all_events,
            "candle_index": self.services.data_fetching.candle_index,
            "nbr_bars": self.services.data_fetching.nbr_bars,
            "track_regime_changes": self.services.indicator_calculation.track_regime_changes,
            "min_rows_required": self.services.strategy_evaluation.min_rows_required,
            "execution_mode": self.services.trade_execution.execution_mode,
            "automation": {
                "enabled": self.automation.enabled,
                "state_file": self.automation.state_file,
                "toggle_file": self.automation.toggle_file,
                "file_watcher_enabled": self.automation.file_watcher_enabled,
                "file_watcher_interval": self.automation.file_watcher_interval,
            },
        }

    def get_data_fetching_config(self, symbol: str) -> Dict[str, Any]:
        """
        Get configuration for DataFetchingService for a specific symbol.

        Args:
            symbol: Trading symbol (e.g., "XAUUSD")

        Returns:
            Configuration dictionary for DataFetchingService
        """
        return {
            "symbol": symbol,
            "timeframes": self.trading.timeframes,
            "candle_index": self.services.data_fetching.candle_index,
            "nbr_bars": self.services.data_fetching.nbr_bars,
        }

    def get_indicator_calculation_config(self, symbol: str) -> Dict[str, Any]:
        """
        Get configuration for IndicatorCalculationService for a specific symbol.

        Args:
            symbol: Trading symbol (e.g., "XAUUSD")

        Returns:
            Configuration dictionary for IndicatorCalculationService
        """
        return {
            "symbol": symbol,
            "timeframes": self.trading.timeframes,
            "track_regime_changes": self.services.indicator_calculation.track_regime_changes,
        }

    def get_strategy_evaluation_config(self, symbol: str) -> Dict[str, Any]:
        """
        Get configuration for StrategyEvaluationService for a specific symbol.

        Args:
            symbol: Trading symbol (e.g., "XAUUSD")

        Returns:
            Configuration dictionary for StrategyEvaluationService
        """
        return {
            "symbol": symbol,
            "min_rows_required": self.services.strategy_evaluation.min_rows_required,
        }

    def get_trade_execution_config(self, symbol: str) -> Dict[str, Any]:
        """
        Get configuration for TradeExecutionService for a specific symbol.

        Args:
            symbol: Trading symbol (e.g., "XAUUSD")

        Returns:
            Configuration dictionary for TradeExecutionService
        """
        return {
            "symbol": symbol,
            "execution_mode": self.services.trade_execution.execution_mode,
            "batch_size": self.services.trade_execution.batch_size,
        }


class ConfigLoader:
    """
    Configuration loader with environment variable overrides.

    Loads configuration from YAML file and applies environment variable overrides.

    Environment variable format:
    - TRADING_SYMBOL -> trading.symbol
    - TRADING_TIMEFRAMES -> trading.timeframes (comma-separated)
    - RISK_DAILY_LOSS_LIMIT -> risk.daily_loss_limit
    - ORCHESTRATOR_ENABLE_AUTO_RESTART -> orchestrator.enable_auto_restart
    - SERVICES_DATA_FETCHING_ENABLED -> services.data_fetching.enabled

    Example:
        ```python
        # Load from default location
        config = ConfigLoader.load()

        # Load from specific file
        config = ConfigLoader.load("config/production.yaml")

        # Access configuration
        print(config.trading.symbol)
        print(config.services.data_fetching.enabled)

        # Get orchestrator config dict
        orchestrator_config = config.to_orchestrator_config()
        ```
    """

    DEFAULT_CONFIG_PATH = "config/services.yaml"

    @classmethod
    def load(
        cls,
        config_path: Optional[str] = None,
        logger: Optional[logging.Logger] = None
    ) -> SystemConfig:
        """
        Load configuration from YAML file with environment variable overrides.

        Args:
            config_path: Path to YAML configuration file (default: config/services.yaml)
            logger: Optional logger for messages

        Returns:
            Validated SystemConfig instance

        Raises:
            FileNotFoundError: If config file doesn't exist
            ValueError: If configuration is invalid
        """
        if logger is None:
            logger = logging.getLogger("config_loader")

        # Determine config path
        if config_path is None:
            config_path = cls.DEFAULT_CONFIG_PATH

        config_file = Path(config_path)

        if not config_file.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")

        # Load YAML
        logger.info(f"Loading configuration from {config_path}")
        with open(config_file, 'r') as f:
            config_dict = yaml.safe_load(f)

        # Apply environment variable overrides
        config_dict = cls._apply_env_overrides(config_dict, logger)

        # Validate and create SystemConfig
        try:
            config = SystemConfig(**config_dict)
            logger.info("Configuration loaded and validated successfully")
            return config
        except Exception as e:
            logger.error(f"Configuration validation failed: {e}")
            raise ValueError(f"Invalid configuration: {e}") from e

    @classmethod
    def _apply_env_overrides(
        cls,
        config_dict: Dict[str, Any],
        logger: logging.Logger
    ) -> Dict[str, Any]:
        """
        Apply environment variable overrides to configuration.

        Args:
            config_dict: Configuration dictionary from YAML
            logger: Logger for messages

        Returns:
            Updated configuration dictionary
        """
        # Trading overrides
        # Check TRADING_SYMBOLS first (new naming), then fall back to SYMBOLS/SYMBOL (legacy .env naming)
        if symbols_env := os.getenv("TRADING_SYMBOLS") or os.getenv("SYMBOLS") or os.getenv("SYMBOL"):
            symbols_list = [s.strip().upper() for s in symbols_env.split(",")]
            env_var_name = (
                "TRADING_SYMBOLS" if os.getenv("TRADING_SYMBOLS")
                else "SYMBOLS" if os.getenv("SYMBOLS")
                else "SYMBOL"
            )
            logger.info(f"Environment override: {env_var_name}={symbols_list}")
            config_dict.setdefault("trading", {})["symbols"] = symbols_list

        # Check TRADING_TIMEFRAMES first, then fall back to TIMEFRAMES (legacy .env naming)
        if timeframes := os.getenv("TRADING_TIMEFRAMES") or os.getenv("TIMEFRAMES"):
            timeframes_list = [tf.strip() for tf in timeframes.split(",")]
            env_var_name = "TRADING_TIMEFRAMES" if os.getenv("TRADING_TIMEFRAMES") else "TIMEFRAMES"
            logger.info(f"Environment override: {env_var_name}={timeframes_list}")
            config_dict.setdefault("trading", {})["timeframes"] = timeframes_list

        # Risk overrides
        if daily_loss_limit := os.getenv("RISK_DAILY_LOSS_LIMIT"):
            try:
                limit = float(daily_loss_limit)
                logger.info(f"Environment override: RISK_DAILY_LOSS_LIMIT={limit}")
                config_dict.setdefault("risk", {})["daily_loss_limit"] = limit
            except ValueError:
                logger.warning(f"Invalid RISK_DAILY_LOSS_LIMIT value: {daily_loss_limit}")

        if max_positions := os.getenv("RISK_MAX_POSITIONS"):
            try:
                positions = int(max_positions)
                logger.info(f"Environment override: RISK_MAX_POSITIONS={positions}")
                config_dict.setdefault("risk", {})["max_positions"] = positions
            except ValueError:
                logger.warning(f"Invalid RISK_MAX_POSITIONS value: {max_positions}")

        # Orchestrator overrides
        if auto_restart := os.getenv("ORCHESTRATOR_ENABLE_AUTO_RESTART"):
            value = auto_restart.lower() in ("true", "1", "yes")
            logger.info(f"Environment override: ORCHESTRATOR_ENABLE_AUTO_RESTART={value}")
            config_dict.setdefault("orchestrator", {})["enable_auto_restart"] = value

        # Service enable/disable overrides
        if data_enabled := os.getenv("SERVICES_DATA_FETCHING_ENABLED"):
            value = data_enabled.lower() in ("true", "1", "yes")
            logger.info(f"Environment override: SERVICES_DATA_FETCHING_ENABLED={value}")
            config_dict.setdefault("services", {}).setdefault("data_fetching", {})["enabled"] = value

        if indicator_enabled := os.getenv("SERVICES_INDICATOR_CALCULATION_ENABLED"):
            value = indicator_enabled.lower() in ("true", "1", "yes")
            logger.info(f"Environment override: SERVICES_INDICATOR_CALCULATION_ENABLED={value}")
            config_dict.setdefault("services", {}).setdefault("indicator_calculation", {})["enabled"] = value

        if strategy_enabled := os.getenv("SERVICES_STRATEGY_EVALUATION_ENABLED"):
            value = strategy_enabled.lower() in ("true", "1", "yes")
            logger.info(f"Environment override: SERVICES_STRATEGY_EVALUATION_ENABLED={value}")
            config_dict.setdefault("services", {}).setdefault("strategy_evaluation", {})["enabled"] = value

        if execution_enabled := os.getenv("SERVICES_TRADE_EXECUTION_ENABLED"):
            value = execution_enabled.lower() in ("true", "1", "yes")
            logger.info(f"Environment override: SERVICES_TRADE_EXECUTION_ENABLED={value}")
            config_dict.setdefault("services", {}).setdefault("trade_execution", {})["enabled"] = value

        # Logging overrides
        if log_level := os.getenv("LOGGING_LEVEL"):
            logger.info(f"Environment override: LOGGING_LEVEL={log_level}")
            config_dict.setdefault("logging", {})["level"] = log_level.upper()

        # Automation overrides
        if automation_enabled := os.getenv("AUTOMATION_ENABLED"):
            value = automation_enabled.lower() in ("true", "1", "yes", "on")
            logger.info(f"Environment override: AUTOMATION_ENABLED={value}")
            config_dict.setdefault("automation", {})["enabled"] = value

        if state_file := os.getenv("AUTOMATION_STATE_FILE"):
            logger.info(f"Environment override: AUTOMATION_STATE_FILE={state_file}")
            config_dict.setdefault("automation", {})["state_file"] = state_file

        if toggle_file := os.getenv("AUTOMATION_TOGGLE_FILE"):
            logger.info(f"Environment override: AUTOMATION_TOGGLE_FILE={toggle_file}")
            config_dict.setdefault("automation", {})["toggle_file"] = toggle_file

        if watcher_enabled := os.getenv("AUTOMATION_FILE_WATCHER_ENABLED"):
            value = watcher_enabled.lower() in ("true", "1", "yes", "on")
            logger.info(f"Environment override: AUTOMATION_FILE_WATCHER_ENABLED={value}")
            config_dict.setdefault("automation", {})["file_watcher_enabled"] = value

        if watcher_interval := os.getenv("AUTOMATION_FILE_WATCHER_INTERVAL"):
            try:
                interval = int(watcher_interval)
                logger.info(f"Environment override: AUTOMATION_FILE_WATCHER_INTERVAL={interval}")
                config_dict.setdefault("automation", {})["file_watcher_interval"] = interval
            except ValueError:
                logger.warning(f"Invalid AUTOMATION_FILE_WATCHER_INTERVAL value: {watcher_interval}")

        return config_dict

    @classmethod
    def create_default_config(cls, output_path: Optional[str] = None) -> None:
        """
        Create a default configuration file.

        Args:
            output_path: Where to write the config file (default: config/services.yaml)
        """
        if output_path is None:
            output_path = cls.DEFAULT_CONFIG_PATH

        # Create default config
        default_config = {
            "services": {
                "data_fetching": {
                    "enabled": True,
                    "fetch_interval": 5,
                    "retry_attempts": 3,
                    "candle_index": 1,
                    "nbr_bars": 3,
                },
                "indicator_calculation": {
                    "enabled": True,
                    "recent_rows_limit": 6,
                    "track_regime_changes": True,
                },
                "strategy_evaluation": {
                    "enabled": True,
                    "evaluation_mode": "on_new_candle",
                    "min_rows_required": 3,
                },
                "trade_execution": {
                    "enabled": True,
                    "execution_mode": "immediate",
                    "batch_size": 1,
                },
            },
            "event_bus": {
                "mode": "synchronous",
                "event_history_limit": 1000,
                "log_all_events": False,
            },
            "orchestrator": {
                "enable_auto_restart": True,
                "health_check_interval": 60,
                "status_log_interval": 10,
            },
            "logging": {
                "level": "INFO",
                "format": "text",
                "correlation_ids": True,
                "file_output": False,
                "log_file": "logs/trading_system.log",
            },
            "trading": {
                "symbols": ["EURUSD"],
                "timeframes": ["1", "5", "15"],
            },
            "risk": {
                "daily_loss_limit": 1000.0,
                "max_positions": 10,
                "max_position_size": 1.0,
            },
        }

        # Create directory if needed
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        # Write YAML
        with open(output_file, 'w') as f:
            yaml.dump(default_config, f, default_flow_style=False, sort_keys=False)

        print(f"Default configuration written to {output_path}")
