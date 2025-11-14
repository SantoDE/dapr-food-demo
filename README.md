# 🍔🍺 Burger & Beer Order System - Dapr Demo

A microservices demo application showcasing Dapr building blocks with a fun burger and beer ordering theme!

## Architecture

```
┌─────────────────┐
│  Order Service  │  ← HTMX Frontend + Flask API
│   (Port 5001)   │     - Places orders
└────────┬────────┘     - Saves to state store
         │              - Publishes to pub/sub
         │
    ┌────┴─────────────────────┐
    │                          │
    ▼                          ▼
┌─────────────┐        ┌─────────────┐
│  Kitchen    │        │    Bar      │
│  Service    │        │  Service    │
│ (Port 5002) │        │ (Port 5003) │
└─────────────┘        └─────────────┘
 Processes 🍔           Processes 🍺
```

## Dapr Building Blocks Demonstrated

1. **State Management**: Redis state store for order persistence
2. **Pub/Sub Messaging**: Redis pub/sub for event-driven communication
3. **Service Invocation**: Services communicate through Dapr sidecars
4. **Configuration**: Dapr configuration for tracing and settings

## Prerequisites

- Python 3.11+
- Dapr CLI (`dapr init`)
- Redis
- Or just use the `devbox.json` provided!

## Quick Start with Devbox

```bash
# Enter the development environment
devbox shell

# Install Python dependencies
pip install -r requirements.txt

# Run all services
chmod +x run-all.sh
./run-all.sh
```

## Manual Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Initialize Dapr

```bash
dapr init
```

### 3. Start Redis

```bash
redis-server
```

### 4. Start Services

In separate terminals:

```bash
# Terminal 1 - Kitchen Service
dapr run --app-id kitchen-service --app-port 5002 --dapr-http-port 3502 --components-path ./components -- python kitchen-service/app.py

# Terminal 2 - Bar Service
dapr run --app-id bar-service --app-port 5003 --dapr-http-port 3503 --components-path ./components -- python bar-service/app.py

# Terminal 3 - Order Service (Frontend)
dapr run --app-id order-service --app-port 5001 --dapr-http-port 3501 --components-path ./components -- python order-service/app.py
```

## Usage

1. Open your browser to `http://localhost:5001`
2. Select burgers and/or beers from the menu
3. Enter your name
4. Click "Place Order"
5. Watch the console logs to see:
   - Order saved to state store
   - Events published to pub/sub topics
   - Kitchen/Bar services processing orders

## View Dapr Dashboard

```bash
dapr dashboard
```

Open `http://localhost:8080` to see:
- Running applications
- Components (state store, pub/sub)
- Service invocations
- Logs and metrics

## How It Works

### Order Flow

1. **Customer places order** via HTMX frontend
2. **Order Service**:
   - Generates order ID
   - Saves order to Redis state store (Dapr State API)
   - Publishes "kitchen-orders" event if burgers ordered
   - Publishes "bar-orders" event if beers ordered
3. **Kitchen Service**:
   - Subscribes to "kitchen-orders" topic
   - Processes burger orders
   - Updates order status in state store
4. **Bar Service**:
   - Subscribes to "bar-orders" topic
   - Processes beer orders
   - Updates order status in state store

### Dapr Components

- **State Store** (`components/statestore.yaml`): Redis for state management
- **Pub/Sub** (`components/pubsub.yaml`): Redis Streams for messaging
- **Config** (`components/config.yaml`): Tracing and app configuration

## Testing

### Place an order via CLI

```bash
curl -X POST http://localhost:5001/api/orders \
  -d "customer_name=John&items=Cheeseburger&items=IPA"
```

### Check state store

```bash
dapr state get --app-id order-service --state-store statestore --key "order-<ORDER_ID>"
```

## Project Structure

```
.
├── order-service/
│   └── app.py          # Frontend + API with HTMX
├── kitchen-service/
│   └── app.py          # Burger order processor
├── bar-service/
│   └── app.py          # Beer order processor
├── components/
│   ├── statestore.yaml # Redis state store config
│   ├── pubsub.yaml     # Redis pub/sub config
│   └── config.yaml     # Dapr configuration
├── requirements.txt
├── devbox.json         # Devbox environment
├── run-all.sh          # Launch script
└── README.md
```

## Learning Points

- **State Management**: See how orders persist across services
- **Pub/Sub**: Event-driven architecture with topic subscriptions
- **Service Discovery**: Services find each other through Dapr
- **Decoupling**: Each service can be developed/deployed independently
- **HTMX**: Modern frontend without heavy JavaScript frameworks

## Next Steps

Want to extend this demo? Try:

- Add workflow orchestration for order completion
- Implement service-to-service invocation
- Add observability with Zipkin tracing
- Deploy to Kubernetes with Dapr
- Add secrets management for API keys
- Implement resiliency policies (retries, circuit breakers)

## Troubleshooting

**Services not communicating?**
- Check Redis is running: `redis-cli ping`
- Verify Dapr is initialized: `dapr --version`
- Check components path is correct

**Port conflicts?**
- Change app ports in run scripts
- Ensure Dapr HTTP ports are unique per service

Enjoy your burger and beer! 🍔🍺
