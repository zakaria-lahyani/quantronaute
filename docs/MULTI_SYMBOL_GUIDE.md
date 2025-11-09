# Multi-Symbol Trading Guide

This guide explains how to use the Quantronaute trading system to trade multiple symbols simultaneously.

## Overview

The multi-symbol trading system allows you to trade multiple instruments (e.g., XAUUSD, BTCUSD, EURUSD) concurrently with:

- **Symbol isolation**: Each symbol has its own services (data fetching, indicators, strategies, execution)
- **Independent configuration**: Per-symbol pip values, position sizes, strategies, and indicators
- **Shared infrastructure**: One EventBus for correlation tracking, one MT5 client
- **Unified monitoring**: Aggregate health checks and metrics across all symbols

### Architecture

```
MultiSymbolTradingOrchestrator
├── Shared EventBus
├── Shared MT5 Client
├── Shared DataSourceManager
├── XAUUSD Services
│   ├── DataFetchingService
│   ├── IndicatorCalculationService
│   ├── StrategyEvaluationService
│   └── TradeExecutionService
├── BTCUSD Services
│   ├── DataFetchingService
│   ├── IndicatorCalculationService
│   ├── StrategyEvaluationService
│   └── TradeExecutionService
└── EURUSD Services
    └── ...
```

## Quick Start

### 1. Configure Symbols

Edit your `.env` file:

```bash
# Multi-symbol trading
SYMBOLS=XAUUSD,BTCUSD,EURUSD

# Default configuration (applies to all symbols)
PIP_VALUE=100
POSITION_SPLIT=4
SCALING_TYPE=equal
ENTRY_SPACING=0.1
RISK_PER_GROUP=1000

# Symbol-specific overrides (optional)
XAUUSD_PIP_VALUE=100
XAUUSD_POSITION_SPLIT=4

BTCUSD_PIP_VALUE=100
BTCUSD_POSITION_SPLIT=2
BTCUSD_ENTRY_SPACING=10.0

EURUSD_PIP_VALUE=10000
EURUSD_POSITION_SPLIT=6
```

### 2. Set Up Configuration Files

Ensure you have strategies and indicators for each symbol:

```
config/
├── strategies/
│   ├── xauusd/
│   │   └── trend_follower.yaml
│   ├── btcusd/
│   │   └── momentum.yaml
│   └── eurusd/
│       └── range_trader.yaml
├── indicators/
│   ├── xauusd/
│   │   ├── xauusd_1.yaml
│   │   └── xauusd_5.yaml
│   ├── btcusd/
│   │   └── btcusd_1.yaml
│   └── eurusd/
│       └── eurusd_1.yaml
└── services.yaml
```

### 3. Run the System

```bash
python app/main_multi_symbol.py
```

## Configuration Details

### Environment Variables

#### Required Variables

- `SYMBOLS`: Comma-separated list of symbols to trade
  - Example: `SYMBOLS=XAUUSD,BTCUSD,EURUSD`
  - Fallback: `SYMBOL=XAUUSD` (single symbol for backward compatibility)

#### Symbol-Specific Variables (Optional)

You can override default configurations per symbol using the pattern `{SYMBOL}_{PARAMETER}`:

- `{SYMBOL}_PIP_VALUE`: Pip value for the symbol
- `{SYMBOL}_POSITION_SPLIT`: Number of position splits
- `{SYMBOL}_SCALING_TYPE`: Scaling type (equal, weighted)
- `{SYMBOL}_ENTRY_SPACING`: Spacing between entries
- `{SYMBOL}_RISK_PER_GROUP`: Risk per position group

**Example:**
```bash
# XAUUSD configuration
XAUUSD_PIP_VALUE=100
XAUUSD_POSITION_SPLIT=4
XAUUSD_RISK_PER_GROUP=1000

# BTCUSD configuration
BTCUSD_PIP_VALUE=100
BTCUSD_POSITION_SPLIT=2
BTCUSD_RISK_PER_GROUP=1500
```

If symbol-specific variables are not provided, the system falls back to default values.

### services.yaml Configuration

Update `config/services.yaml`:

```yaml
trading:
  symbols: ["XAUUSD", "BTCUSD"]  # Can be overridden by SYMBOLS env var
  timeframes: ["1", "5", "15"]

# Rest of configuration remains the same
```

## Strategy Configuration

Each symbol can have its own strategies. Create YAML files in `config/strategies/{symbol}/`:

### Example: XAUUSD Strategy

`config/strategies/xauusd/trend_follower.yaml`:

```yaml
name: trend_follower
timeframes: ["1", "5"]
entry:
  long:
    mode: all
    conditions:
      - signal: ema_20
        operator: GREATER_THAN
        value: ema_50
        timeframe: "1"
risk:
  position_sizing:
    type: percentage
    value: 1.0
  sl:
    type: monetary
    value: 500.0
  tp:
    type: rr
    value: 2.0
```

### Example: BTCUSD Strategy

`config/strategies/btcusd/momentum.yaml`:

```yaml
name: momentum_strategy
timeframes: ["1"]
entry:
  long:
    mode: all
    conditions:
      - signal: rsi
        operator: LESS_THAN
        value: 30
        timeframe: "1"
risk:
  position_sizing:
    type: percentage
    value: 0.5
  sl:
    type: monetary
    value: 1000.0
```

## Indicator Configuration

Each symbol can have different indicators. Create YAML files in `config/indicators/{symbol}/`:

### Example: XAUUSD Indicators

`config/indicators/xauusd/xauusd_1.yaml`:

```yaml
indicators:
  ema:
    enabled: true
    params:
      short_period: 20
      long_period: 50
  rsi:
    enabled: true
    params:
      period: 14
```

### Example: BTCUSD Indicators

`config/indicators/btcusd/btcusd_1.yaml`:

```yaml
indicators:
  ema:
    enabled: true
    params:
      short_period: 12
      long_period: 26
  macd:
    enabled: true
    params:
      fast_period: 12
      slow_period: 26
      signal_period: 9
```

## Monitoring and Metrics

### Health Monitoring

The system monitors health for each symbol independently:

```python
health_status = orchestrator.get_service_health()
# Returns:
{
    "XAUUSD": {
        "data_fetching": True,
        "indicator_calculation": True,
        "strategy_evaluation": True,
        "trade_execution": True
    },
    "BTCUSD": {
        "data_fetching": True,
        "indicator_calculation": False,  # Unhealthy!
        "strategy_evaluation": True,
        "trade_execution": True
    }
}
```

### Metrics

Get comprehensive metrics for all symbols:

```python
metrics = orchestrator.get_all_metrics()
# Returns metrics per symbol:
{
    "orchestrator": {
        "status": "running",
        "symbols": ["XAUUSD", "BTCUSD"],
        "total_services": 8,
        "uptime_seconds": 3600
    },
    "services": {
        "XAUUSD": {
            "data_fetching": {
                "data_fetches": 120,
                "new_candles_detected": 45
            },
            "strategy_evaluation": {
                "strategies_evaluated": 45,
                "entry_signals_generated": 12,
                "exit_signals_generated": 5
            },
            ...
        },
        "BTCUSD": { ... }
    },
    "event_bus": {
        "events_published": 5420,
        "event_types_subscribed": 8
    }
}
```

## Auto-Restart on Failures

If a service for one symbol fails, it can be automatically restarted without affecting other symbols:

```yaml
# config/services.yaml
orchestrator:
  enable_auto_restart: true
  health_check_interval: 60  # seconds
```

## Advanced Usage

### Programmatic Configuration

You can create the orchestrator programmatically:

```python
from app.infrastructure.multi_symbol_orchestrator import MultiSymbolTradingOrchestrator
from app.infrastructure.config import SystemConfig, TradingConfig

# Create configuration
config = SystemConfig(
    trading=TradingConfig(
        symbols=["XAUUSD", "BTCUSD", "EURUSD"],
        timeframes=["1", "5", "15"]
    )
)

# Load components for each symbol
symbol_components = load_all_components_for_symbols(
    symbols=["XAUUSD", "BTCUSD", "EURUSD"],
    env_config=env_config,
    client=client,
    data_source=data_source,
    date_helper=date_helper,
    logger=logger
)

# Create orchestrator
orchestrator = MultiSymbolTradingOrchestrator.from_config(
    config=config,
    client=client,
    data_source=data_source,
    symbol_components=symbol_components,
    date_helper=date_helper,
    logger=logger
)

# Start trading
orchestrator.start()
orchestrator.run(interval_seconds=5)
```

### Enabling/Disabling Symbols

To temporarily disable a symbol without removing configuration:

1. **Remove from SYMBOLS env var:**
   ```bash
   # .env
   SYMBOLS=XAUUSD,EURUSD  # Removed BTCUSD
   ```

2. **Restart the system**

## Troubleshooting

### Symbol Not Trading

**Problem:** One symbol is not generating trades

**Solutions:**
1. Check if strategy files exist: `config/strategies/{symbol}/`
2. Check if indicator files exist: `config/indicators/{symbol}/`
3. Check logs for symbol-specific errors
4. Verify symbol-specific configuration values

### Service Health Check Failures

**Problem:** Health checks failing for specific symbol

**Solutions:**
1. Check service logs for that symbol
2. Verify historical data loaded correctly
3. Check indicator configuration validity
4. Enable auto-restart in services.yaml

### High Memory Usage

**Problem:** Memory usage increases with multiple symbols

**Solutions:**
1. Reduce `recent_rows_limit` in services.yaml
2. Decrease `nbr_bars` in data fetching config
3. Limit number of concurrent symbols
4. Monitor per-symbol memory usage

## Migration from Single-Symbol

If you're migrating from single-symbol trading:

1. **Update .env file:**
   ```bash
   # Old
   SYMBOL=XAUUSD

   # New
   SYMBOLS=XAUUSD
   ```

2. **Use new entry point:**
   ```bash
   # Old
   python app/main_orchestrated.py

   # New
   python app/main_multi_symbol.py
   ```

3. **Configuration stays the same** - Existing single-symbol configs work as-is

## Best Practices

1. **Start with 2-3 symbols**: Don't overload the system initially
2. **Use symbol-specific configs**: Tailor pip values and position sizes per symbol
3. **Monitor resource usage**: Check CPU/memory with multiple symbols
4. **Separate strategies**: Different symbols often need different approaches
5. **Test thoroughly**: Backtest each symbol individually first
6. **Use auto-restart**: Enable service auto-restart for resilience

## FAQ

**Q: Can I trade more than 10 symbols?**
A: Yes, but monitor performance. The system scales well, but depends on your hardware.

**Q: Do all symbols need the same timeframes?**
A: No. Each symbol's timeframes are determined by its indicator configuration files.

**Q: Can I add/remove symbols without restarting?**
A: Currently no. You need to restart the system to change the symbol list.

**Q: How are daily loss limits handled?**
A: Daily loss limit is currently global across all symbols. Per-symbol limits are a future enhancement.

**Q: Can symbols share strategies?**
A: No. Each symbol loads strategies from its own folder. However, you can duplicate YAML files across folders.

## Next Steps

- [Architecture Documentation](ARCHITECTURE.md)
- [Event-Driven Services](MIGRATION_GUIDE.md)
- [Configuration Reference](../config/services.yaml)
