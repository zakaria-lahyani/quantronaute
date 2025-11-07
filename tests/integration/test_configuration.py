"""
Integration tests for configuration system.

These tests verify that configuration loading, validation, and
environment variable overrides work correctly.
"""

import pytest
import os
import tempfile
from pathlib import Path
import yaml

from app.infrastructure.config import (
    ConfigLoader,
    SystemConfig,
    DataFetchingConfig,
    IndicatorCalculationConfig,
    StrategyEvaluationConfig,
    TradeExecutionConfig,
    EventBusConfig,
    OrchestratorConfig,
    LoggingConfig,
    TradingConfig,
    RiskConfig,
)


class TestConfigurationLoading:
    """Test configuration loading from YAML files."""

    @pytest.fixture
    def temp_config_file(self):
        """Create a temporary configuration file."""
        config_data = {
            "services": {
                "data_fetching": {
                    "enabled": True,
                    "fetch_interval": 10,
                    "retry_attempts": 5,
                    "candle_index": 1,
                    "nbr_bars": 5,
                },
                "indicator_calculation": {
                    "enabled": True,
                    "recent_rows_limit": 10,
                    "track_regime_changes": True,
                },
                "strategy_evaluation": {
                    "enabled": True,
                    "evaluation_mode": "on_new_candle",
                    "min_rows_required": 5,
                },
                "trade_execution": {
                    "enabled": True,
                    "execution_mode": "batch",
                    "batch_size": 3,
                },
            },
            "event_bus": {
                "mode": "synchronous",
                "event_history_limit": 500,
                "log_all_events": True,
            },
            "orchestrator": {
                "enable_auto_restart": False,
                "health_check_interval": 120,
                "status_log_interval": 20,
            },
            "logging": {
                "level": "DEBUG",
                "format": "json",
                "correlation_ids": True,
                "file_output": True,
                "log_file": "logs/test.log",
            },
            "trading": {
                "symbol": "GBPUSD",
                "timeframes": ["5", "15", "30"],
            },
            "risk": {
                "daily_loss_limit": 500.0,
                "max_positions": 5,
                "max_position_size": 0.5,
            },
        }

        with tempfile.NamedTemporaryFile(
            mode='w', suffix='.yaml', delete=False
        ) as f:
            yaml.dump(config_data, f)
            temp_path = f.name

        yield temp_path

        # Cleanup
        Path(temp_path).unlink()

    def test_load_config_from_file(self, temp_config_file):
        """Test loading configuration from YAML file."""
        config = ConfigLoader.load(config_path=temp_config_file)

        # Verify loaded correctly
        assert isinstance(config, SystemConfig)
        assert config.trading.symbol == "GBPUSD"
        assert config.trading.timeframes == ["5", "15", "30"]
        assert config.services.data_fetching.fetch_interval == 10
        assert config.services.trade_execution.execution_mode == "batch"
        assert config.orchestrator.enable_auto_restart is False

    def test_config_validation(self):
        """Test that configuration validation catches invalid values."""
        # Test invalid timeframes (empty list)
        with pytest.raises(Exception):
            SystemConfig(
                trading=TradingConfig(symbol="EURUSD", timeframes=[])
            )

        # Test invalid fetch_interval (negative)
        with pytest.raises(Exception):
            DataFetchingConfig(fetch_interval=-1)

        # Test invalid daily_loss_limit (negative)
        with pytest.raises(Exception):
            RiskConfig(daily_loss_limit=-100.0)

    def test_default_values(self):
        """Test that default values are applied correctly."""
        config = SystemConfig(
            trading=TradingConfig(symbol="EURUSD", timeframes=["1", "5"])
        )

        # Verify defaults
        assert config.services.data_fetching.enabled is True
        assert config.services.data_fetching.fetch_interval == 5
        assert config.event_bus.mode == "synchronous"
        assert config.orchestrator.enable_auto_restart is True
        assert config.risk.daily_loss_limit == 1000.0

    def test_config_to_orchestrator_config(self, temp_config_file):
        """Test conversion to orchestrator configuration."""
        config = ConfigLoader.load(config_path=temp_config_file)

        orch_config = config.to_orchestrator_config()

        # Verify structure
        assert "symbol" in orch_config
        assert "timeframes" in orch_config
        assert "enable_auto_restart" in orch_config
        assert "event_history_limit" in orch_config

        # Verify values
        assert orch_config["symbol"] == "GBPUSD"
        assert orch_config["timeframes"] == ["5", "15", "30"]
        assert orch_config["enable_auto_restart"] is False

    def test_service_config_extraction(self, temp_config_file):
        """Test extracting configuration for individual services."""
        config = ConfigLoader.load(config_path=temp_config_file)

        # Data fetching config
        data_config = config.get_data_fetching_config()
        assert data_config["symbol"] == "GBPUSD"
        assert data_config["candle_index"] == 1
        assert data_config["nbr_bars"] == 5

        # Indicator config
        indicator_config = config.get_indicator_calculation_config()
        assert indicator_config["symbol"] == "GBPUSD"
        assert indicator_config["track_regime_changes"] is True

        # Strategy config
        strategy_config = config.get_strategy_evaluation_config()
        assert strategy_config["symbol"] == "GBPUSD"
        assert strategy_config["min_rows_required"] == 5

        # Execution config
        execution_config = config.get_trade_execution_config()
        assert execution_config["symbol"] == "GBPUSD"
        assert execution_config["execution_mode"] == "batch"
        assert execution_config["batch_size"] == 3


class TestEnvironmentVariableOverrides:
    """Test environment variable overrides."""

    @pytest.fixture
    def temp_config_file(self):
        """Create a temporary configuration file."""
        config_data = {
            "trading": {
                "symbol": "EURUSD",
                "timeframes": ["1", "5"],
            },
            "risk": {
                "daily_loss_limit": 1000.0,
                "max_positions": 10,
            },
            "orchestrator": {
                "enable_auto_restart": True,
            },
            "services": {
                "data_fetching": {
                    "enabled": True,
                },
            },
        }

        with tempfile.NamedTemporaryFile(
            mode='w', suffix='.yaml', delete=False
        ) as f:
            yaml.dump(config_data, f)
            temp_path = f.name

        yield temp_path

        Path(temp_path).unlink()

    def test_trading_symbol_override(self, temp_config_file):
        """Test TRADING_SYMBOL environment variable override."""
        os.environ["TRADING_SYMBOL"] = "GBPUSD"

        try:
            config = ConfigLoader.load(config_path=temp_config_file)
            assert config.trading.symbol == "GBPUSD"
        finally:
            del os.environ["TRADING_SYMBOL"]

    def test_trading_timeframes_override(self, temp_config_file):
        """Test TRADING_TIMEFRAMES environment variable override."""
        os.environ["TRADING_TIMEFRAMES"] = "15,30,60"

        try:
            config = ConfigLoader.load(config_path=temp_config_file)
            assert config.trading.timeframes == ["15", "30", "60"]
        finally:
            del os.environ["TRADING_TIMEFRAMES"]

    def test_risk_daily_loss_limit_override(self, temp_config_file):
        """Test RISK_DAILY_LOSS_LIMIT environment variable override."""
        os.environ["RISK_DAILY_LOSS_LIMIT"] = "2000.0"

        try:
            config = ConfigLoader.load(config_path=temp_config_file)
            assert config.risk.daily_loss_limit == 2000.0
        finally:
            del os.environ["RISK_DAILY_LOSS_LIMIT"]

    def test_risk_max_positions_override(self, temp_config_file):
        """Test RISK_MAX_POSITIONS environment variable override."""
        os.environ["RISK_MAX_POSITIONS"] = "5"

        try:
            config = ConfigLoader.load(config_path=temp_config_file)
            assert config.risk.max_positions == 5
        finally:
            del os.environ["RISK_MAX_POSITIONS"]

    def test_orchestrator_auto_restart_override(self, temp_config_file):
        """Test ORCHESTRATOR_ENABLE_AUTO_RESTART environment variable override."""
        os.environ["ORCHESTRATOR_ENABLE_AUTO_RESTART"] = "false"

        try:
            config = ConfigLoader.load(config_path=temp_config_file)
            assert config.orchestrator.enable_auto_restart is False
        finally:
            del os.environ["ORCHESTRATOR_ENABLE_AUTO_RESTART"]

    def test_service_enable_override(self, temp_config_file):
        """Test service enable/disable environment variable override."""
        os.environ["SERVICES_DATA_FETCHING_ENABLED"] = "false"

        try:
            config = ConfigLoader.load(config_path=temp_config_file)
            assert config.services.data_fetching.enabled is False
        finally:
            del os.environ["SERVICES_DATA_FETCHING_ENABLED"]

    def test_logging_level_override(self, temp_config_file):
        """Test LOGGING_LEVEL environment variable override."""
        os.environ["LOGGING_LEVEL"] = "ERROR"

        try:
            config = ConfigLoader.load(config_path=temp_config_file)
            assert config.logging.level == "ERROR"
        finally:
            del os.environ["LOGGING_LEVEL"]

    def test_multiple_overrides(self, temp_config_file):
        """Test multiple environment variable overrides at once."""
        os.environ["TRADING_SYMBOL"] = "USDJPY"
        os.environ["RISK_DAILY_LOSS_LIMIT"] = "750.0"
        os.environ["ORCHESTRATOR_ENABLE_AUTO_RESTART"] = "false"

        try:
            config = ConfigLoader.load(config_path=temp_config_file)
            assert config.trading.symbol == "USDJPY"
            assert config.risk.daily_loss_limit == 750.0
            assert config.orchestrator.enable_auto_restart is False
        finally:
            del os.environ["TRADING_SYMBOL"]
            del os.environ["RISK_DAILY_LOSS_LIMIT"]
            del os.environ["ORCHESTRATOR_ENABLE_AUTO_RESTART"]

    def test_invalid_environment_variable_ignored(self, temp_config_file):
        """Test that invalid environment variable values are ignored."""
        os.environ["RISK_DAILY_LOSS_LIMIT"] = "invalid_number"

        try:
            # Should not raise error, just use default value
            config = ConfigLoader.load(config_path=temp_config_file)
            # Should use value from file, not invalid env var
            assert config.risk.daily_loss_limit == 1000.0
        finally:
            del os.environ["RISK_DAILY_LOSS_LIMIT"]


class TestConfigurationEdgeCases:
    """Test configuration edge cases and error handling."""

    def test_missing_config_file(self):
        """Test that missing config file raises appropriate error."""
        with pytest.raises(FileNotFoundError):
            ConfigLoader.load(config_path="non_existent_file.yaml")

    def test_invalid_yaml(self):
        """Test that invalid YAML raises appropriate error."""
        with tempfile.NamedTemporaryFile(
            mode='w', suffix='.yaml', delete=False
        ) as f:
            f.write("invalid: yaml: content: [[[")
            temp_path = f.name

        try:
            with pytest.raises(Exception):
                ConfigLoader.load(config_path=temp_path)
        finally:
            Path(temp_path).unlink()

    def test_missing_required_fields(self):
        """Test that missing required fields raises validation error."""
        with tempfile.NamedTemporaryFile(
            mode='w', suffix='.yaml', delete=False
        ) as f:
            # Missing trading.symbol (required field)
            yaml.dump({
                "trading": {
                    "timeframes": ["1", "5"]
                }
            }, f)
            temp_path = f.name

        try:
            with pytest.raises(ValueError):
                ConfigLoader.load(config_path=temp_path)
        finally:
            Path(temp_path).unlink()

    def test_create_default_config(self):
        """Test creating default configuration file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "default_config.yaml"

            ConfigLoader.create_default_config(output_path=str(output_path))

            # Verify file created
            assert output_path.exists()

            # Verify can be loaded
            config = ConfigLoader.load(config_path=str(output_path))
            assert isinstance(config, SystemConfig)
            assert config.trading.symbol == "EURUSD"

    def test_minimal_config(self):
        """Test that minimal configuration with only required fields works."""
        with tempfile.NamedTemporaryFile(
            mode='w', suffix='.yaml', delete=False
        ) as f:
            yaml.dump({
                "trading": {
                    "symbol": "EURUSD",
                    "timeframes": ["1"]
                }
            }, f)
            temp_path = f.name

        try:
            config = ConfigLoader.load(config_path=temp_path)

            # Verify defaults applied
            assert config.trading.symbol == "EURUSD"
            assert config.services.data_fetching.enabled is True
            assert config.orchestrator.enable_auto_restart is True
        finally:
            Path(temp_path).unlink()
