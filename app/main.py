from app.clients.mt5.client import create_client_with_retry
from app.strategy_builder.factory import StrategyEngineFactory

# Load strategies from configuration
engine = StrategyEngineFactory.create_engine(
    config_paths=["../config/dummy.yaml"],
    logger_name="trading-engine"
)

# Get strategy configurations
strategies = {
    name: engine.get_strategy_info(name)
    for name in engine.list_available_strategies()
}

print(strategies)

client_endpoint = "http://127.0.0.1:8000/mt5"

client = create_client_with_retry(client_endpoint)

print(client)
account = client.account.get_account_info()
print(f"Balance: {account['balance']}")

positions = client.positions.get_open_positions()
print(positions)

# Get positions by symbol
eurusd_positions = client.positions.get_positions_by_symbol("EURUSD")
print(eurusd_positions)
xauusd_positions = client.positions.get_positions_by_symbol("XAUUSD")
print(xauusd_positions)

