#!/bin/bash

echo "🍔🍺 Starting Burger & Beer Order System with Dapr"
echo "=================================================="

# Check if Dapr CLI is available
if ! command -v dapr &> /dev/null; then
    echo "❌ Error: Dapr CLI not found!"
    echo "Please install Dapr CLI or enter the devbox shell with 'devbox shell'"
    exit 1
fi

# Check if Dapr is initialized by checking for daprd binary
if [ ! -f "$HOME/.dapr/bin/daprd" ]; then
    echo "Initializing Dapr runtime..."
    dapr init --dev
else
    echo "✅ Dapr runtime already initialized"
fi

echo ""
echo "🚀 Starting all services with Dapr Multi-App Run..."
echo ""
echo "Services:"
echo "  - Order Service (Frontend):  http://localhost:5001"
echo "  - Kitchen Service:            http://localhost:5002"
echo "  - Bar Service:                http://localhost:5003"
echo "  - Dapr Dashboard:             http://localhost:8080 (run 'dapr dashboard' in another terminal)"
echo ""
echo "Press Ctrl+C to stop all services"
echo ""

# Trap SIGINT and SIGTERM to properly stop dapr
cleanup() {
    echo ""
    echo "🛑 Stopping all services..."
    dapr stop -f dapr.yaml
    exit 0
}

trap cleanup SIGINT SIGTERM

# Run all services using Dapr multi-app run
dapr run -f dapr.yaml &
DAPR_PID=$!

# Wait for dapr process
wait $DAPR_PID
