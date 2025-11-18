#!/bin/bash

echo "🍔🍺 Starting Burger & Beer Order System with Dapr"
echo "=================================================="

# Check if Dapr CLI is available
if ! command -v dapr &> /dev/null; then
    echo "❌ Error: Dapr CLI not found!"
    echo "Please install Dapr CLI or enter the devbox shell with 'devbox shell'"
    exit 1
fi

# Check if Docker Compose is available
if ! command -v docker-compose &> /dev/null && ! command -v docker &> /dev/null; then
    echo "⚠️  Warning: Docker/Docker Compose not found! Observability stack won't start."
    SKIP_OBSERVABILITY=true
else
    SKIP_OBSERVABILITY=false
fi

# Check if Dapr is initialized by checking for daprd binary
if [ ! -f "$HOME/.dapr/bin/daprd" ]; then
    echo "Initializing Dapr runtime..."
    dapr init --dev
else
    echo "✅ Dapr runtime already initialized"
fi

# Start observability stack
if [ "$SKIP_OBSERVABILITY" = false ]; then
    echo ""
    echo "🔍 Starting Jaeger tracing backend..."

    # Check if docker compose v2 or v1 syntax
    if docker compose version &> /dev/null; then
        DOCKER_COMPOSE_CMD="docker compose"
    else
        DOCKER_COMPOSE_CMD="docker-compose"
    fi

    $DOCKER_COMPOSE_CMD -f docker-compose.observability.yaml up -d

    if [ $? -eq 0 ]; then
        echo "✅ Jaeger started successfully"
        echo "   - Jaeger UI:         http://localhost:16686"
        echo "   - OTLP gRPC:         localhost:4317"
        echo "   - OTLP HTTP:         localhost:4318"
    else
        echo "⚠️  Warning: Failed to start Jaeger"
    fi
fi

echo ""
echo "🚀 Starting all services with Dapr Multi-App Run..."
echo ""
echo "Services:"
echo "  - Order Service (Frontend):  http://localhost:5001"
echo "  - Kitchen Service:            http://localhost:5002"
echo "  - Bar Service:                http://localhost:5003"
echo "  - Dapr Dashboard:             http://localhost:8080 (run 'dapr dashboard' in another terminal)"
if [ "$SKIP_OBSERVABILITY" = false ]; then
echo "  - Jaeger Tracing UI:          http://localhost:16686"
fi
echo ""
echo "Press Ctrl+C to stop all services"
echo ""

# Trap SIGINT and SIGTERM to properly stop dapr and docker
cleanup() {
    echo ""
    echo "🛑 Stopping all services..."
    dapr stop -f dapr.yaml

    if [ "$SKIP_OBSERVABILITY" = false ]; then
        echo "🛑 Stopping Jaeger..."
        $DOCKER_COMPOSE_CMD -f docker-compose.observability.yaml down
    fi

    exit 0
}

trap cleanup SIGINT SIGTERM

# Run all services using Dapr multi-app run
dapr run -f dapr.yaml &
DAPR_PID=$!

# Wait for dapr process
wait $DAPR_PID
