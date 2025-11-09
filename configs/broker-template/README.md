# Broker Configuration Template

This directory serves as a template for creating new broker configurations.

## Creating a New Broker Configuration

1. **Copy this template directory:**
   ```bash
   cp -r configs/broker-template configs/broker-{name}
   ```

2. **Create environment file:**
   ```bash
   cp configs/broker-{name}/.env.broker.example configs/broker-{name}/.env.broker
   ```

3. **Customize the environment file (`.env.broker`):**
   - Set `API_BASE_URL` to your broker's API endpoint
   - Configure `SYMBOLS` you want to trade
   - Adjust risk parameters (`DAILY_LOSS_LIMIT`, `RISK_PER_GROUP`, etc.)
   - Set symbol-specific parameters if needed

4. **Customize the configuration files:**
   - Edit `services.yaml` for service-specific settings
   - Modify strategies in `strategies/{symbol}/` directories
   - Adjust indicator configurations in `indicators/`
   - Set trading restrictions in `restrictions/`

5. **Add to docker-compose.yml:**
   ```yaml
   broker-{name}:
     build: .
     image: quantronaute:latest
     container_name: quantronaute-broker-{name}
     volumes:
       - ./configs/broker-{name}:/app/config:ro
     env_file:
       - ./configs/broker-{name}/.env.broker
     restart: unless-stopped
     networks:
       - trading-network
   ```

6. **Start your broker container:**
   ```bash
   docker-compose up -d broker-{name}
   ```

## Configuration Structure

- **`.env.broker`**: Environment variables (API endpoint, symbols, risk parameters)
- **`.env.broker.example`**: Template for environment variables
- **`services.yaml`**: Main service configuration (data fetching, orchestrator, event bus, etc.)
- **`strategies/`**: Trading strategies organized by symbol
- **`indicators/`**: Indicator configurations
- **`restrictions/`**: Trading restrictions (news events, market close times, etc.)

## Important Notes

- Each broker can have completely different strategies and risk parameters
- Environment variables are loaded from `.env.broker` file
- Configuration files are mounted read-only to the container
- To update a broker's config, modify the files and restart the container
- All paths in the container will reference `/app/config`
- Keep `.env.broker` secure and never commit it to version control
