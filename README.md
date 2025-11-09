# quantronaute

## Table of Contents
- [Docker Deployment (Multi-Broker)](#docker-deployment-multi-broker)
- [Local Development Setup](#local-development-setup)
- [Position Sizing](#position-sizing)
- [Stop Loss Types](#stop-loss-types)
- [Take Profit Types](#take-profit-types)

---

## Docker Deployment (Multi-Broker)

Deploy the quantronaute trading system across multiple brokers using Docker. Each broker runs in an isolated container with its own configuration and strategies.

### Quick Start

1. **Build the Docker image:**
   ```bash
   docker build -t quantronaute:latest .
   ```

2. **Start all brokers:**
   ```bash
   docker-compose up -d
   ```

3. **View logs:**
   ```bash
   docker-compose logs -f broker-a
   ```

### Architecture

Each broker container:
- Runs the same application code (single Docker image)
- Has its own isolated configuration directory mounted from `configs/broker-{name}/`
- Connects to a different broker API endpoint
- Can use completely different trading strategies and risk parameters

### Pre-configured Brokers

The docker-compose includes 3 example brokers:

- **broker-a**: Conservative strategy (XAUUSD, BTCUSD)
- **broker-b**: Aggressive forex (EURUSD, GBPUSD)
- **broker-c**: Balanced multi-symbol

### Adding a New Broker

1. **Create broker configuration:**
   ```bash
   cp -r configs/broker-template configs/broker-d
   ```

2. **Create environment file:**
   ```bash
   cp configs/broker-d/.env.broker.example configs/broker-d/.env.broker
   ```

3. **Edit the environment file (`configs/broker-d/.env.broker`):**
   - Set your broker's `API_BASE_URL`
   - Configure `SYMBOLS` to trade
   - Adjust risk parameters (`DAILY_LOSS_LIMIT`, etc.)

4. **Customize configuration files:**
   - Edit `configs/broker-d/services.yaml`
   - Modify strategies in `configs/broker-d/strategies/`
   - Adjust indicators in `configs/broker-d/indicators/`
   - Set restrictions in `configs/broker-d/restrictions/`

5. **Add service to docker-compose.yml:**
   ```yaml
   broker-d:
     build: .
     image: quantronaute:latest
     container_name: quantronaute-broker-d
     volumes:
       - ./configs/broker-d:/app/config:ro
     env_file:
       - ./configs/broker-d/.env.broker
     restart: unless-stopped
     networks:
       - trading-network
   ```

6. **Start the new broker:**
   ```bash
   docker-compose up -d broker-d
   ```

### Docker Management Commands

```bash
# Start all brokers
docker-compose up -d

# Start specific broker
docker-compose up -d broker-a

# Stop specific broker
docker-compose stop broker-a

# View logs for all brokers
docker-compose logs -f

# View logs for specific broker
docker-compose logs -f broker-a

# Restart broker (after config changes)
docker-compose restart broker-a

# Stop all brokers
docker-compose down

# Rebuild and restart
docker-compose up -d --build
```

### Configuration Management

Each broker's configuration is stored in `configs/broker-{name}/`:

```
configs/broker-a/
├── .env.broker         # Environment variables (API, symbols, risk params)
├── .env.broker.example # Template for environment variables
├── services.yaml       # Service configuration
├── strategies/         # Trading strategies per symbol
│   ├── xauusd/
│   └── btcusd/
├── indicators/         # Indicator configurations
└── restrictions/       # Trading restrictions
```

**To update a broker's configuration:**

1. **Environment variables** (API endpoint, symbols, risk params):
   - Edit `configs/broker-{name}/.env.broker`
   - Restart the broker: `docker-compose restart broker-{name}`

2. **Strategies/indicators/restrictions**:
   - Edit files in `configs/broker-{name}/strategies/`, `indicators/`, or `restrictions/`
   - Restart the broker: `docker-compose restart broker-{name}`

### Environment Variables

Each broker uses an `.env.broker` file located in its configuration directory. See [.env.docker.template](.env.docker.template) for all available environment variables and detailed documentation.

**Key variables per broker:**
- `API_BASE_URL`: Broker API endpoint (REQUIRED)
- `ACCOUNT_TYPE`: daily or swing (REQUIRED)
- `SYMBOLS`: Comma-separated symbols (REQUIRED)
- `TRADE_MODE`: live or backtest (REQUIRED)
- `DAILY_LOSS_LIMIT`: Maximum daily loss
- Symbol-specific: `{SYMBOL}_PIP_VALUE`, `{SYMBOL}_RISK_PER_GROUP`, etc.

**Example:** Edit `configs/broker-a/.env.broker` to change broker A's settings without affecting other brokers.

---

## Local Development Setup

### Create a virtual env
- python -m venv venv
- .\venv\Scripts\Activate.ps1
- pip install -r requirements.txt
---

## Position Sizing
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

## Stop Loss Types

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

## Take Profit Types

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

## Advanced Combinations

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

## Recommendations for Your Use Case

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

