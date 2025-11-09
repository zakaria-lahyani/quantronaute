import os
import yaml
from typing import Any, Dict
from dotenv import load_dotenv

from app.utils.logger import AppLogger


class YamlConfigurationManager:
    """YAML-based configuration manager."""

    def load_schema(self, path: str) -> Dict[str, Any]:
        """Load validation schema from YAML file."""
        try:
            with open(path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            raise FileNotFoundError(f"Schema file not found: {path}")
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML in schema file {path}: {e}")

    def load_config(self, path: str) -> Dict[str, Any]:
        """Load configuration from YAML file."""
        try:
            with open(path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            raise FileNotFoundError(f"Config file not found: {path}")
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML in config file {path}: {e}")


class LoadEnvironmentVariables:
    def __init__(self, conf_path):
        self.conf_path = conf_path
        self.ACCOUNT_TYPE = ""
        self.API_BASE_URL = ""
        self.API_TIMEOUT = ""

        # Multi-symbol support: SYMBOLS takes precedence, falls back to SYMBOL for backward compatibility
        self.SYMBOLS = []  # List of symbols to trade
        self.SYMBOL = ""   # Legacy: single symbol (kept for backward compatibility)

        self.CONF_FOLDER_PATH = ""

        # Symbol-specific configurations (dict by symbol)
        self.SYMBOL_CONFIGS = {}  # Maps symbol -> {pip_value, position_split, etc.}

        # Legacy single-symbol config (kept for backward compatibility)
        self.PIP_VALUE = 0
        self.POSITION_SPLIT = 0
        self.SCALING_TYPE = ""
        self.ENTRY_SPACING = 0
        self.RISK_PER_GROUP = 0

        self.TRADE_MODE = ""
        self.BACKTEST_DATA_PATH = ""
        self.DAILY_LOSS_LIMIT = 0.0

        self.RESTRICTION_CONF_FOLDER_PATH = ""
        self.DEFAULT_CLOSE_TIME = ""
        self.NEWS_RESTRICTION_DURATION = 5
        self.MARKET_CLOSE_RESTRICTION_DURATION = 5
        self._load_env_variables()

    def _load_env_variables(self):
        """Load environment variables from the .env file."""
        dotenv_path = self.conf_path
        if not os.path.exists(dotenv_path):
            raise FileNotFoundError(f"{dotenv_path} file not found.")

        load_dotenv(dotenv_path)

        # API Configuration
        self.ACCOUNT_TYPE = os.getenv('ACCOUNT_TYPE')
        self.API_BASE_URL = os.getenv('API_BASE_URL')
        self.API_TIMEOUT = int(os.getenv('API_TIMEOUT'))

        # Symbol Configuration
        # Priority: SYMBOLS > SYMBOL (for backward compatibility)
        symbols_env = os.getenv('SYMBOLS')
        if symbols_env:
            # Multi-symbol mode
            self.SYMBOLS = [s.strip().upper() for s in symbols_env.split(',')]
            self.SYMBOL = self.SYMBOLS[0]  # Set first symbol as default for legacy code
        else:
            # Single-symbol mode (backward compatibility)
            self.SYMBOL = os.getenv('SYMBOL', 'XAUUSD').upper()
            self.SYMBOLS = [self.SYMBOL]

        # Paths
        self.CONF_FOLDER_PATH = os.getenv('CONF_FOLDER_PATH')
        self.BACKTEST_DATA_PATH = os.getenv('BACKTEST_DATA_PATH')
        self.RESTRICTION_CONF_FOLDER_PATH = os.getenv('RESTRICTION_CONF_FOLDER_PATH')

        # Trading Mode
        self.TRADE_MODE = os.getenv('TRADE_MODE', 'live')

        # Risk Configuration
        self.DAILY_LOSS_LIMIT = float(os.getenv('DAILY_LOSS_LIMIT', '5000'))

        # Legacy single-symbol configuration (for backward compatibility)
        self.PIP_VALUE = int(os.getenv('PIP_VALUE', '100'))
        self.POSITION_SPLIT = int(os.getenv('POSITION_SPLIT', '1'))
        self.SCALING_TYPE = os.getenv('SCALING_TYPE', 'equal')
        self.ENTRY_SPACING = float(os.getenv('ENTRY_SPACING', '0.1'))
        self.RISK_PER_GROUP = float(os.getenv('RISK_PER_GROUP', '1000'))

        # Time Configuration
        self.DEFAULT_CLOSE_TIME = os.getenv('DEFAULT_CLOSE_TIME')
        self.NEWS_RESTRICTION_DURATION = int(os.getenv('NEWS_RESTRICTION_DURATION', '5'))
        self.MARKET_CLOSE_RESTRICTION_DURATION = int(os.getenv('MARKET_CLOSE_RESTRICTION_DURATION', '5'))

        # Load symbol-specific configurations
        self._load_symbol_configs()

    def _load_symbol_configs(self):
        """
        Load symbol-specific configurations from environment variables.

        Supports pattern: {SYMBOL}_PIP_VALUE, {SYMBOL}_POSITION_SPLIT, etc.
        Falls back to default values if symbol-specific config not found.
        """
        for symbol in self.SYMBOLS:
            symbol_upper = symbol.upper().replace('/', '_')  # Handle symbols like EUR/USD

            # Symbol-specific configurations (if provided)
            pip_value = os.getenv(f'{symbol_upper}_PIP_VALUE')
            position_split = os.getenv(f'{symbol_upper}_POSITION_SPLIT')
            scaling_type = os.getenv(f'{symbol_upper}_SCALING_TYPE')
            entry_spacing = os.getenv(f'{symbol_upper}_ENTRY_SPACING')
            risk_per_group = os.getenv(f'{symbol_upper}_RISK_PER_GROUP')

            self.SYMBOL_CONFIGS[symbol] = {
                'pip_value': int(pip_value) if pip_value else self.PIP_VALUE,
                'position_split': int(position_split) if position_split else self.POSITION_SPLIT,
                'scaling_type': scaling_type if scaling_type else self.SCALING_TYPE,
                'entry_spacing': float(entry_spacing) if entry_spacing else self.ENTRY_SPACING,
                'risk_per_group': float(risk_per_group) if risk_per_group else self.RISK_PER_GROUP,
            }

    def get_symbol_config(self, symbol: str) -> Dict[str, Any]:
        """
        Get configuration for a specific symbol.

        Args:
            symbol: Trading symbol (e.g., "XAUUSD")

        Returns:
            Dictionary with symbol-specific configuration
        """
        symbol_upper = symbol.upper()
        if symbol_upper in self.SYMBOL_CONFIGS:
            return self.SYMBOL_CONFIGS[symbol_upper]

        # Fallback to default configuration
        return {
            'pip_value': self.PIP_VALUE,
            'position_split': self.POSITION_SPLIT,
            'scaling_type': self.SCALING_TYPE,
            'entry_spacing': self.ENTRY_SPACING,
            'risk_per_group': self.RISK_PER_GROUP,
        }
