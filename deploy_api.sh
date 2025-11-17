#!/bin/bash
#
# Quick deployment script for Manual Trading API
#
# Usage:
#   ./deploy_api.sh                    # Deploy standalone
#   ./deploy_api.sh --integrated       # Deploy with trading system
#   ./deploy_api.sh --stop             # Stop API
#   ./deploy_api.sh --logs             # View logs
#   ./deploy_api.sh --test             # Run tests

set -e

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Configuration
COMPOSE_FILE="docker-compose.api.yml"
CONTAINER_NAME="quantronaute-api"
API_PORT=8080

# Helper functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."

    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed. Please install Docker first."
        exit 1
    fi

    if ! command -v docker-compose &> /dev/null; then
        log_error "Docker Compose is not installed. Please install Docker Compose first."
        exit 1
    fi

    log_success "Prerequisites OK"
}

# Check if .env.api exists
check_env_file() {
    if [ ! -f ".env.api" ]; then
        log_warning ".env.api file not found. Creating template..."
        cat > .env.api << 'EOF'
# JWT Configuration
API_SECRET_KEY=CHANGE-THIS-IN-PRODUCTION-USE-RANDOM-STRING
API_ACCESS_TOKEN_EXPIRE_MINUTES=60
API_REFRESH_TOKEN_EXPIRE_DAYS=7

# Admin User Credentials
# Generate with: python -c "from passlib.context import CryptContext; pwd_context = CryptContext(schemes=['bcrypt'], deprecated='auto'); print(f'API_USER_ADMIN=admin:{pwd_context.hash(\"YOUR_PASSWORD\")}')"
API_USER_ADMIN=admin:$2b$12$CHANGE_THIS_HASH

# MT5 API Connection (optional - for integrated mode)
API_BASE_URL=http://host.docker.internal:8000/mt5

# Account Type
ACCOUNT_TYPE=swing
EOF
        log_warning "Created .env.api template. Please update with your credentials!"
        log_warning "Generate password hash with:"
        log_warning "  python -c \"from passlib.context import CryptContext; pwd_context = CryptContext(schemes=['bcrypt'], deprecated='auto'); print(f'API_USER_ADMIN=admin:{pwd_context.hash(\\\"YOUR_PASSWORD\\\")}')\""
        return 1
    fi
    return 0
}

# Build Docker image
build_image() {
    log_info "Building Docker image..."
    docker-compose -f $COMPOSE_FILE build --no-cache
    log_success "Docker image built successfully"
}

# Start API container
start_api() {
    log_info "Starting API container..."
    docker-compose -f $COMPOSE_FILE up -d

    # Wait for container to be healthy
    log_info "Waiting for API to be ready..."
    sleep 5

    # Check if container is running
    if docker ps | grep -q $CONTAINER_NAME; then
        log_success "API container is running"

        # Test health endpoint
        if curl -s http://localhost:$API_PORT/health > /dev/null 2>&1; then
            log_success "API is responding at http://localhost:$API_PORT"
            echo ""
            echo "API Endpoints:"
            echo "  Health:         http://localhost:$API_PORT/health"
            echo "  Documentation:  http://localhost:$API_PORT/docs"
            echo "  Login:          http://localhost:$API_PORT/auth/login"
            echo ""
            echo "Test with:"
            echo "  curl -X POST http://localhost:$API_PORT/auth/login \\"
            echo "    -H 'Content-Type: application/json' \\"
            echo "    -d '{\"username\":\"admin\",\"password\":\"your_password\"}'"
        else
            log_warning "API container is running but not responding yet"
            log_info "Check logs with: ./deploy_api.sh --logs"
        fi
    else
        log_error "Failed to start API container"
        log_info "Check logs with: docker-compose -f $COMPOSE_FILE logs"
        exit 1
    fi
}

# Stop API container
stop_api() {
    log_info "Stopping API container..."
    docker-compose -f $COMPOSE_FILE down
    log_success "API container stopped"
}

# View logs
view_logs() {
    docker-compose -f $COMPOSE_FILE logs -f api
}

# Run tests
run_tests() {
    log_info "Running API tests..."

    # Check if API is running
    if ! docker ps | grep -q $CONTAINER_NAME; then
        log_error "API container is not running. Start it first with: ./deploy_api.sh"
        exit 1
    fi

    # Run test client
    if [ -f "test_api_client.py" ]; then
        log_info "Running test client..."
        python test_api_client.py
    else
        log_warning "test_api_client.py not found"
        log_info "Testing manually with curl..."

        echo ""
        echo "Testing health endpoint..."
        curl -s http://localhost:$API_PORT/health | python -m json.tool || log_error "Health check failed"

        echo ""
        echo "Testing login endpoint..."
        echo "Replace 'your_password' with actual password:"
        echo "curl -X POST http://localhost:$API_PORT/auth/login \\"
        echo "  -H 'Content-Type: application/json' \\"
        echo "  -d '{\"username\":\"admin\",\"password\":\"your_password\"}'"
    fi
}

# Show status
show_status() {
    log_info "API Container Status:"
    docker-compose -f $COMPOSE_FILE ps

    if docker ps | grep -q $CONTAINER_NAME; then
        echo ""
        log_info "Container Logs (last 20 lines):"
        docker-compose -f $COMPOSE_FILE logs --tail=20 api

        echo ""
        log_info "Resource Usage:"
        docker stats --no-stream $CONTAINER_NAME
    fi
}

# Integrated deployment
deploy_integrated() {
    log_info "Deploying API with trading system integration..."

    # Check if trading system is running
    if ! docker ps | grep -q "mt5-api"; then
        log_warning "MT5 API container not found. Make sure trading system is running first."
        log_info "Start trading system with: docker-compose up -d"
    fi

    # Start API
    start_api
}

# Main script
main() {
    case "${1:-}" in
        --build)
            check_prerequisites
            build_image
            ;;
        --stop)
            stop_api
            ;;
        --logs)
            view_logs
            ;;
        --test)
            run_tests
            ;;
        --status)
            show_status
            ;;
        --integrated)
            check_prerequisites
            if check_env_file; then
                deploy_integrated
            fi
            ;;
        --rebuild)
            check_prerequisites
            stop_api
            build_image
            if check_env_file; then
                start_api
            fi
            ;;
        --help)
            echo "Usage: ./deploy_api.sh [OPTION]"
            echo ""
            echo "Options:"
            echo "  (none)          Deploy API in standalone mode"
            echo "  --integrated    Deploy API with trading system integration"
            echo "  --build         Build Docker image only"
            echo "  --rebuild       Stop, rebuild, and start API"
            echo "  --stop          Stop API container"
            echo "  --logs          View API logs (follow mode)"
            echo "  --test          Run API tests"
            echo "  --status        Show API status and logs"
            echo "  --help          Show this help message"
            echo ""
            echo "Examples:"
            echo "  ./deploy_api.sh                 # Deploy standalone"
            echo "  ./deploy_api.sh --integrated    # Deploy with trading system"
            echo "  ./deploy_api.sh --logs          # View logs"
            echo "  ./deploy_api.sh --test          # Run tests"
            ;;
        *)
            # Default: standalone deployment
            check_prerequisites
            if check_env_file; then
                start_api
            else
                log_error "Please configure .env.api file first"
                exit 1
            fi
            ;;
    esac
}

# Run main
main "$@"
