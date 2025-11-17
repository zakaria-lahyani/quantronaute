# Quantronaute Trading System Documentation

## Documentation Index

### Core Concepts

1. **[Account Types](./account-types.md)** - Daily vs Swing account configuration and behavior
   - Daily accounts: Automatic daily closure, intraday trading only
   - Swing accounts: Multi-day positions, overnight holding allowed
   - News event handling for both account types
   - Configuration examples and troubleshooting

2. **[Manual Trading API](./api-usage.md)** - REST API for monitoring and controlling the trading system
   - Real-time account, position, and indicator monitoring
   - Manual trade execution and automation control
   - JWT authentication and security
   - See also: [API Integration Guide](./api-integration.md)

### Quick Reference

#### Account Type Selection

| Account Type | Use Case | Overnight Positions | Auto Close |
|--------------|----------|---------------------|------------|
| `daily` | Day trading, FTMO Daily challenges | ❌ No | ✅ Yes |
| `swing` | Swing trading, trend following | ✅ Yes | ❌ No |

#### Essential Configuration

```bash
# .env.broker
ACCOUNT_TYPE=daily                    # or "swing"
SYMBOLS=XAUUSD,BTCUSD
DAILY_LOSS_LIMIT=5000

# Daily accounts only
DEFAULT_CLOSE_TIME=16:55:00
MARKET_CLOSE_RESTRICTION_DURATION=30

# All accounts
NEWS_RESTRICTION_DURATION=2
```

### Configuration Files

- **economic-calendar.csv** - High-impact news events (required for all accounts)
- **holidays.csv** - Special market close times (required for daily accounts)
- **.env.broker** - Environment variables per broker/container
- **services.yaml** - Service configuration and risk parameters

### Related Documentation

- [Main README](../README.md) - Overall system documentation
- [Event Persistence Analysis](../tasks/event-persistence-analysis.md) - Event system documentation
- [Docker Deployment](../README.md#docker-deployment) - Multi-broker Docker setup

---

## Need Help?

For questions or issues:
1. Check the [Account Types](./account-types.md) documentation
2. Review configuration examples in `configs/broker-template/`
3. Check logs for detailed error messages
4. Verify environment variables are set correctly
