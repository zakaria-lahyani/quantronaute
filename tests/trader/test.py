# 1. Configure position scaling
from datetime import datetime
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.strategy_builder.data.dtos import EntryDecision, StopLossResult, TakeProfitResult, TPLevel
from app.trader.risk_manager.models import ScalingConfig
from app.trader.risk_manager.risk_calculator import RiskCalculator

scaling_config = ScalingConfig(
    num_entries=4,  # Split into 4 positions
    scaling_type="equal",  # 25% each
    entry_spacing=0.1,  # 0.5% spacing between entries
    max_risk_per_group=1000.0  #
)

# 2. Create trader_claude
trader = RiskCalculator(scaling_config)

# 3. Example entry decision (from your entry_manager.manage_trades)
entry_decision = EntryDecision(
    symbol='XAUUSD',
    strategy_name='test-strategy',
    magic=12345,
    direction='long',
    entry_signals='BUY',
    entry_price=3000.0,
    position_size=1,
    stop_loss=StopLossResult(
        type='monetary',
        level=2995.0,
        trailing=False
    ),
    take_profit=TakeProfitResult(
        type='multi_target',
        targets=[
            TPLevel(level=3005.38, value=1.0, percent=60.0, move_stop=True),
            TPLevel(level=3010.76, value=2.0, percent=40.0, move_stop=False)
        ]
    ),
    decision_time=datetime.now()
)

current_price = 3001.0  # Current market price

result = trader.process_entry_signal(entry_decision, current_price)
print(result)


entry_decision = EntryDecision(
    symbol='BTCUSD',
    strategy_name='anchors-transitions-and-htf-bias',
    magic=180493240,
    direction='short',
    entry_signals='SELL',
    entry_price=117400.69,
    position_size=1,
    stop_loss=StopLossResult(type='fixed', level=118400, step=0.004, trailing=True, source=None),
    take_profit=TakeProfitResult(
        type='multi_target',
        level=115400,
        source=None,
        percent=None,
        targets=None
    ),
    decision_time=datetime.now()
)

current_price = 117401.0  # Current market price

result = trader.process_entry_signal(entry_decision, current_price)
print(result)
