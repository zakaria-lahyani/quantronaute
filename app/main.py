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