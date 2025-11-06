# Utils Package

## Overview

The **utils** package provides common utilities, configuration loading, logging setup, helper functions, and date/time operations used throughout the quantronaute trading system. It serves as the foundation layer providing essential services to all other packages.

## Main Features

- **Configuration Management**: YAML config loading and .env file parsing
- **Centralized Logging**: Consistent logging across all modules
- **Date/Time Operations**: Timezone-aware datetime utilities
- **Helper Functions**: Magic number generation, candle detection, etc.
- **Type-Safe Configuration**: Pydantic models for environment variables
- **Reusable Utilities**: Common functions used across packages

## Package Structure

```
utils/
├── config.py           # Configuration loading (YAML & .env)
├── logger.py          # Centralized logging setup
├── date_helper.py     # Date/time utilities
└── functions_helper.py # Helper functions
```

## Key Components

### Configuration Management

#### YamlConfigurationManager

Loads and manages YAML configuration files:

```python
from app.utils.config import YamlConfigurationManager

# Create configuration manager
config_manager = YamlConfigurationManager()

# Load YAML configuration
config = config_manager.load_config('config/indicators/eurusd/1.yaml')

# Access configuration
print(config['indicators']['ema']['params']['short_period'])
```

#### LoadEnvironmentVariables

Loads and validates environment variables from .env file:

```python
from app.utils.config import LoadEnvironmentVariables

# Load environment variables
config = LoadEnvironmentVariables(".env")

# Access typed configuration
print(config.trade_mode)        # "live" or "backtest"
print(config.symbol)            # "EURUSD"
print(config.daily_loss_limit)  # 1000.0
print(config.api_base_url)      # "http://localhost:8000"
```

**Configuration Model**:
```python
class EnvironmentConfig:
    # Trading mode
    trade_mode: str              # "live" or "backtest"
    symbol: str                  # Trading symbol

    # API configuration
    api_base_url: str           # MT5 API URL
    api_timeout: int            # Request timeout

    # Risk management
    daily_loss_limit: float     # Maximum daily loss
    max_positions: int          # Maximum concurrent positions

    # Order configuration
    position_split: int         # Order splitting
    scaling_type: str           # "equal" or "pyramid"
    entry_spacing: float        # Price spacing
    risk_per_group: float       # Risk per order group

    # Restrictions
    restriction_conf_folder_path: str
    default_close_time: str
    news_restriction_duration: int
    market_close_restriction_duration: int

    # Backtest configuration
    backtest_data_path: str     # Path to parquet files
```

### Logging

#### AppLogger

Centralized logging configuration:

```python
from app.utils.logger import AppLogger

# Get logger for module
logger = AppLogger.get_logger("my_module")

# Use logger
logger.info("Information message")
logger.warning("Warning message")
logger.error("Error message")
logger.debug("Debug message")
```

**Log Format**:
```
2024-01-15 14:30:25,123 - my_module - INFO - Information message
2024-01-15 14:30:26,456 - my_module - WARNING - Warning message
2024-01-15 14:30:27,789 - my_module - ERROR - Error message
```

**Configuration**:
```python
# Configure logging
AppLogger.configure(
    level="INFO",              # Log level
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),  # Console output
        logging.FileHandler("trading.log")  # File output
    ]
)
```

### Date/Time Utilities

#### DateHelper

Timezone-aware date/time operations:

```python
from app.utils.date_helper import DateHelper

date_helper = DateHelper()

# Get current date/time
now = date_helper.now()

# Get today's date
today = date_helper.today()

# Get date N days ago
thirty_days_ago = date_helper.get_date_days_ago(30)

# Get start of day
start_of_day = date_helper.get_start_of_day()

# Get end of day
end_of_day = date_helper.get_end_of_day()

# Format date for display
formatted = date_helper.format_date(now)

# Parse date string
parsed = date_helper.parse_date("2024-01-15")
```

**Common Use Cases**:

```python
# Historical data fetching
start_date = date_helper.get_date_days_ago(30)
end_date = date_helper.today()
data = data_manager.get_historical_data("EURUSD", "1", start_date, end_date)

# Daily P&L calculation
start_of_day = date_helper.get_start_of_day()
daily_trades = get_trades_since(start_of_day)

# Trading hours check
current_hour = date_helper.now().hour
if 8 <= current_hour <= 17:
    # Trading hours
    pass
```

### Helper Functions

#### Magic Number Generation

Generate unique identifiers for trades:

```python
from app.utils.functions_helper import generate_magic_number

# Generate magic number for strategy
magic = generate_magic_number(
    strategy_name="trend_follower",
    symbol="EURUSD",
    timeframes=["1", "5"],
    direction="long"
)

print(magic)  # e.g., 1234567890

# Magic numbers are deterministic:
# Same inputs always produce same magic number
magic2 = generate_magic_number("trend_follower", "EURUSD", ["1", "5"], "long")
assert magic == magic2  # True
```

#### Candle Pattern Detection

Detect candlestick patterns:

```python
from app.utils.functions_helper import is_bullish_candle, is_bearish_candle

# Check if candle is bullish
is_bullish = is_bullish_candle(open=1.0900, close=1.0950)
# Returns: True (close > open)

# Check if candle is bearish
is_bearish = is_bearish_candle(open=1.0950, close=1.0900)
# Returns: True (close < open)

# Use in strategy conditions
if is_bullish_candle(row['open'], row['close']):
    logger.info("Bullish candle detected")
```

## Usage Examples

### Complete Configuration Setup

```python
from app.utils.config import LoadEnvironmentVariables, YamlConfigurationManager
from app.utils.logger import AppLogger
from app.utils.date_helper import DateHelper

# 1. Setup logging
logger = AppLogger.get_logger(__name__)

# 2. Load environment configuration
env_config = LoadEnvironmentVariables(".env")

logger.info(f"Trade mode: {env_config.trade_mode}")
logger.info(f"Symbol: {env_config.symbol}")

# 3. Load YAML configurations
config_manager = YamlConfigurationManager()

indicator_configs = {
    '1': config_manager.load_config('config/indicators/eurusd/1.yaml'),
    '5': config_manager.load_config('config/indicators/eurusd/5.yaml'),
}

# 4. Create date helper
date_helper = DateHelper()

# 5. Use throughout application
logger.info(f"Current time: {date_helper.now()}")
```

### Logging Best Practices

```python
from app.utils.logger import AppLogger

# Get logger for module
logger = AppLogger.get_logger(__name__)

# Info: General information
logger.info("Trading cycle started")

# Debug: Detailed information for debugging
logger.debug(f"Processing {len(entries)} entry decisions")

# Warning: Warning messages
logger.warning("No positions to close")

# Error: Error messages with context
try:
    result = risky_operation()
except Exception as e:
    logger.error(f"Operation failed: {e}", exc_info=True)

# Critical: Critical errors
logger.critical("Daily loss limit exceeded - stopping trading")
```

### Date/Time Operations

```python
from app.utils.date_helper import DateHelper

date_helper = DateHelper()

# Get historical data for last 30 days
start_date = date_helper.get_date_days_ago(30)
end_date = date_helper.today()

historical_data = data_manager.get_historical_data(
    symbol="EURUSD",
    timeframe="1",
    start_date=start_date,
    end_date=end_date
)

# Calculate daily P&L
start_of_day = date_helper.get_start_of_day()
today_trades = [t for t in trades if t['time'] >= start_of_day]
daily_pnl = sum(t['profit'] for t in today_trades)

# Check trading hours
now = date_helper.now()
if now.weekday() < 5 and 8 <= now.hour < 17:
    logger.info("Within trading hours")
else:
    logger.info("Outside trading hours")
```

### Magic Number Usage

```python
from app.utils.functions_helper import generate_magic_number

# Generate unique magic number per strategy/direction
def create_entry_decision(strategy_name, symbol, direction):
    magic = generate_magic_number(
        strategy_name=strategy_name,
        symbol=symbol,
        timeframes=["1", "5"],
        direction=direction
    )

    return EntryDecision(
        symbol=symbol,
        strategy_name=strategy_name,
        magic=magic,
        direction=direction,
        # ... other fields
    )

# Close positions by magic number
def close_strategy_positions(strategy_name, symbol, direction):
    magic = generate_magic_number(strategy_name, symbol, ["1", "5"], direction)

    # Find positions with matching magic number
    positions = [p for p in open_positions if p['magic'] == magic]

    # Close all matching positions
    for position in positions:
        trader.close_position(position['ticket'])
```

## Configuration Files

### .env File Example

```bash
# Trading Mode
TRADE_MODE=live

# Symbol
SYMBOL=EURUSD

# API Configuration
API_BASE_URL=http://localhost:8000
API_TIMEOUT=30

# Risk Management
DAILY_LOSS_LIMIT=1000.0
MAX_POSITIONS=10

# Order Configuration
POSITION_SPLIT=3
SCALING_TYPE=equal
ENTRY_SPACING=0.0005
RISK_PER_GROUP=500.0

# Restrictions
RESTRICTION_CONF_FOLDER_PATH=./config/restrictions
DEFAULT_CLOSE_TIME=16:55
NEWS_RESTRICTION_DURATION=5
MARKET_CLOSE_RESTRICTION_DURATION=5

# Backtest Configuration
BACKTEST_DATA_PATH=./data
```

### YAML Configuration Example

```yaml
# config/indicators/eurusd/1.yaml
indicators:
  ema:
    enabled: true
    params:
      short_period: 20
      long_period: 50
    outputs:
      - ema_20
      - ema_50

  rsi:
    enabled: true
    params:
      period: 14
    outputs:
      - rsi

  atr:
    enabled: true
    params:
      period: 14
    outputs:
      - atr
```

## Integration Points

### With All Packages

Every package uses utils for:

#### Configuration Loading
```python
# In any module
from app.utils.config import LoadEnvironmentVariables

config = LoadEnvironmentVariables(".env")
```

#### Logging
```python
# In any module
from app.utils.logger import AppLogger

logger = AppLogger.get_logger(__name__)
logger.info("Module initialized")
```

#### Date Operations
```python
# In any module
from app.utils.date_helper import DateHelper

date_helper = DateHelper()
today = date_helper.today()
```

## Best Practices

### 1. Use Module-Level Loggers

```python
# At top of module
from app.utils.logger import AppLogger

logger = AppLogger.get_logger(__name__)

# Use throughout module
def some_function():
    logger.info("Function called")
```

### 2. Load Configuration Once

```python
# At application startup
config = LoadEnvironmentVariables(".env")

# Pass to components that need it
data_manager = DataSourceManager(
    mode=config.trade_mode,
    # ...
)
```

### 3. Use DateHelper for Consistency

```python
# Always use DateHelper for dates
from app.utils.date_helper import DateHelper

date_helper = DateHelper()

# Don't use datetime.now() directly
# now = datetime.now()  # Avoid

# Use DateHelper instead
now = date_helper.now()  # Timezone-aware
```

### 4. Validate Configuration

```python
# Validate after loading
config = LoadEnvironmentVariables(".env")

if config.trade_mode not in ["live", "backtest"]:
    raise ValueError(f"Invalid trade mode: {config.trade_mode}")

if config.daily_loss_limit <= 0:
    raise ValueError("Daily loss limit must be positive")
```

### 5. Appropriate Log Levels

```python
# DEBUG: Detailed diagnostic information
logger.debug(f"Processing row: {row}")

# INFO: General informational messages
logger.info("Trading cycle completed")

# WARNING: Warning messages
logger.warning("No data available")

# ERROR: Error messages
logger.error("Failed to execute trade")

# CRITICAL: Critical issues
logger.critical("System shutdown")
```

## Advanced Features

### Custom Configuration Loading

```python
from app.utils.config import YamlConfigurationManager

class CustomConfigManager(YamlConfigurationManager):
    def load_strategy_configs(self, folder_path):
        """Load all strategy configs from folder."""
        configs = {}

        for file in os.listdir(folder_path):
            if file.endswith('.yaml'):
                strategy_name = file.replace('.yaml', '')
                configs[strategy_name] = self.load_config(
                    os.path.join(folder_path, file)
                )

        return configs
```

### Date Range Utilities

```python
from app.utils.date_helper import DateHelper

date_helper = DateHelper()

def get_date_range(days):
    """Get date range for last N days."""
    end_date = date_helper.today()
    start_date = date_helper.get_date_days_ago(days)
    return start_date, end_date

def is_trading_day(date):
    """Check if date is a weekday."""
    return date.weekday() < 5  # Monday = 0, Friday = 4

def is_trading_hours(time):
    """Check if time is within trading hours."""
    return 8 <= time.hour < 17
```

### Magic Number Utilities

```python
from app.utils.functions_helper import generate_magic_number

def get_strategy_positions(strategy_name, symbol, direction, all_positions):
    """Get positions for specific strategy."""
    magic = generate_magic_number(strategy_name, symbol, ["1", "5"], direction)
    return [p for p in all_positions if p['magic'] == magic]

def has_open_position(strategy_name, symbol, direction, all_positions):
    """Check if strategy has open position."""
    positions = get_strategy_positions(strategy_name, symbol, direction, all_positions)
    return len(positions) > 0
```

## Troubleshooting

### Configuration Not Loading

**Issue**: Configuration file not found
**Solutions**:
1. Check file path is correct
2. Verify file exists
3. Use absolute paths if needed
4. Check file permissions

### Logging Not Working

**Issue**: Log messages not appearing
**Solutions**:
1. Check log level (DEBUG vs INFO)
2. Verify logger name
3. Configure handlers properly
4. Check file permissions for file logging

### Date/Time Issues

**Issue**: Incorrect dates or timezones
**Solutions**:
1. Always use DateHelper
2. Ensure timezone configuration
3. Check system time/timezone
4. Validate date parsing

## Testing

```python
import pytest
from app.utils.config import LoadEnvironmentVariables
from app.utils.date_helper import DateHelper
from app.utils.functions_helper import generate_magic_number

def test_environment_config():
    """Test environment configuration loading."""
    config = LoadEnvironmentVariables(".env.test")

    assert config.trade_mode in ["live", "backtest"]
    assert config.symbol == "EURUSD"
    assert config.daily_loss_limit > 0

def test_date_helper():
    """Test date helper utilities."""
    date_helper = DateHelper()

    now = date_helper.now()
    today = date_helper.today()

    assert now.date() == today.date()

    thirty_days_ago = date_helper.get_date_days_ago(30)
    assert (today - thirty_days_ago).days == 30

def test_magic_number():
    """Test magic number generation."""
    magic1 = generate_magic_number("strategy1", "EURUSD", ["1"], "long")
    magic2 = generate_magic_number("strategy1", "EURUSD", ["1"], "long")

    # Same inputs produce same magic number
    assert magic1 == magic2

    # Different inputs produce different magic numbers
    magic3 = generate_magic_number("strategy2", "EURUSD", ["1"], "long")
    assert magic1 != magic3
```

## Performance Considerations

1. **Configuration Caching**: Load config once, reuse throughout
2. **Logger Instances**: Create once per module, not per function
3. **Date Operations**: Minimal overhead, safe to use frequently
4. **Magic Numbers**: Fast hash-based generation

## Conclusion

The utils package provides essential utilities that form the foundation of the quantronaute trading system. Its configuration management, logging, and helper functions ensure consistency and maintainability across all packages.

**Key Benefits**:
- **Centralized Configuration**: Single source of truth
- **Consistent Logging**: Uniform logging across all modules
- **Type Safety**: Pydantic validation for configuration
- **Reusability**: Common utilities available everywhere
- **Maintainability**: Easy to update and extend
