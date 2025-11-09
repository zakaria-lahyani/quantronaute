# quantronaute

### create a virtual env  
- python -m venv venv
- .\venv\Scripts\Activate.ps1
- pip install -r requirements.txt


# POsition sizing
  1. Percentage (Current): Best for consistent risk management
  position_sizing:
    type: percentage
    value: 1.0  # 1% of $100k = $1000 position
  sl:
    type: monetary
    value: 500.0  # Exactly $500 risk
  2. Fixed: Good for specific dollar amounts
  position_sizing:
    type: fixed
    value: 1000.0  # Always $1000 position
  sl:
    type: monetary
    value: 500.0  # Exactly $500 risk
  3. Volatility: Advanced, requires volatility indicators
  position_sizing:
    type: volatility
    value: 2.0  # Base 2% risk, adjusted by volatility
  sl:
    type: monetary
    value: 500.0  # Exactly $500 risk


  ---
   STOP LOSS TYPES

  1. Fixed Stop Loss (type: "fixed")

  How it works: Sets stop loss at a fixed distance from entry price.

  Configuration:
  sl:
    type: fixed
    value: 50.0  # 50 pips from entry
    trailing:    # Optional trailing feature
      enabled: true
      step: 10.0

  Features:
  - Fixed pip distance from entry
  - Optional trailing functionality
  - Can be percentage-based or absolute
  - Risk-reward ratio calculation

  ---
  2. Trailing Stop Loss (type: "trailing")

  How it works: Follows price movement, only moving in favorable direction.

  Configuration:
  sl:
    type: trailing
    step: 20.0             # Trailing step in pips
    activation_price: 30.0  # When to start trailing
    cap: 100.0             # Maximum trailing distance

  Features:
  - Automatically follows profitable moves
  - Never moves against you
  - Configurable activation threshold
  - Protects profits while allowing upside

  ---
  3. Indicator-Based Stop Loss (type: "indicator")

  How it works: Uses technical indicators (ATR, Support/Resistance, etc.) for dynamic stops.

  Configuration:
  sl:
    type: indicator
    source: "ATR"        # Indicator name
    offset: 1.5          # Multiplier/offset
    timeframe: "1"       # Indicator timeframe
    trailing:            # Optional trailing
      enabled: true
      step: 5.0

  Features:
  - Dynamic based on market conditions
  - Uses ATR, Bollinger Bands, Support/Resistance
  - Adapts to volatility
  - Can include trailing functionality

  ---
  4. Monetary Stop Loss (type: "monetary") ⭐ New - You added this

  How it works: Limits loss to exact dollar amount regardless of price/position size.

  Configuration:
  sl:
    type: monetary
    value: 500.0    # Exactly $500 max loss
    trailing: false # Optional trailing

  Features:
  - Exact dollar risk control
  - Independent of entry price
  - Works with any position size
  - Perfect for consistent risk management

  ---
  🎯 TAKE PROFIT TYPES

  1. Fixed Take Profit (type: "fixed")

  How it works: Sets take profit at fixed distance/percentage from entry.

  Configuration:
  tp:
    type: fixed
    value: 100.0  # 100 pips profit or 1% if percentage mode

  Features:
  - Simple fixed target
  - Can be pips or percentage
  - Risk-reward ratio calculation
  - Position value calculation at TP

  ---
  2. Multi-Target Take Profit (type: "multi_target") ⭐ Currently using

  How it works: Multiple profit targets with partial position closing.

  Configuration:
  tp:
    type: multi_target
    targets:
      - value: 1.0        # 1% profit target
        percent: 60       # Close 60% of position
        move_stop: true   # Move stop to breakeven
      - value: 2.0        # 2% profit target
        percent: 40       # Close remaining 40%
        move_stop: false  # Don't move stop

  Features:
  - Partial Exits: Close portions at different levels
  - Risk Management: Move stops after targets hit
  - Flexible Allocation: Any percentage distribution
  - Automatic Execution: System manages multiple targets
  - Profit Protection: Lock in gains progressively

  Advanced capabilities:
  - Track executed vs. remaining targets
  - Calculate remaining position size
  - Automatic stop loss movement
  - Execution summary and planning

  ---
  💡 ADVANCED COMBINATIONS

  Example 1: Conservative Risk Management

  risk:
    position_sizing:
      type: percentage
      value: 1.0
    sl:
      type: monetary
      value: 500.0      # Max $500 loss
    tp:
      type: multi_target
      targets:
        - value: 1.0    # Take 50% at 1:1 risk/reward
          percent: 50
          move_stop: true
        - value: 2.0    # Take remaining 50% at 1:2
          percent: 50
          move_stop: false

  Example 2: Volatility-Adaptive System

  risk:
    position_sizing:
      type: volatility
      value: 2.0
    sl:
      type: indicator
      source: "ATR"
      offset: 2.0
      timeframe: "1"
    tp:
      type: fixed
      value: 150.0    # Fixed 150 pip target

  Example 3: Aggressive Profit Taking

  risk:
    sl:
      type: trailing
      step: 15.0
      activation_price: 25.0
    tp:
      type: multi_target
      targets:
        - value: 0.5    # Quick 20% exit at 0.5%
          percent: 20
          move_stop: true
        - value: 1.0    # 40% exit at 1%
          percent: 40
          move_stop: true
        - value: 2.5    # Let 40% run to 2.5%
          percent: 40
          move_stop: false

  ---
  🔧 RECOMMENDATIONS FOR YOUR USE CASE

  For $500 max loss with multiple profit targets, your current setup is optimal:

  risk:
    position_sizing:
      type: percentage
      value: 1.0
    sl:
      type: monetary
      value: 500.0    # Exactly $500 risk
    tp:
      type: multi_target
      targets:
        - value: 1.0    # 60% at 1% profit
          percent: 60
          move_stop: true  # Protect capital
        - value: 2.0    # 40% at 2% profit
          percent: 40
          move_stop: false # Let it run

