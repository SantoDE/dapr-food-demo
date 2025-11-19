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
- Dapr CLI
- Docker & Docker Compose (for observability stack)
- Or just use the `devbox.json` provided!

## Quick Start

### Option 1: One-Command Startup (Recommended)

The easiest way to run the entire system:

```bash
# Make script executable (first time only)
chmod +x run-all.sh

# Start everything
./run-all.sh
```

**What the script does:**
- ✅ Checks and initializes Dapr if needed
- 🔍 Starts Jaeger for distributed tracing
- 🚀 Launches all three services using Dapr Multi-App Run
- 📊 Provides links to all UIs and dashboards

**Access the application:**
- **Order Service (Frontend)**: http://localhost:5001
- **Jaeger Tracing UI**: http://localhost:16686
- **Dapr Dashboard**: Run `dapr dashboard` in another terminal, then visit http://localhost:8080

Press `Ctrl+C` to stop all services gracefully.

### Option 2: Using Devbox

```bash
# Enter the development environment (includes all dependencies)
devbox shell

# Run all services
./run-all.sh
```

## Manual Setup (Advanced)

If you prefer to run services individually or customize the setup:

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Initialize Dapr

```bash
dapr init --dev
```

### 3. Start Observability Stack (Optional)

```bash
docker compose -f docker-compose.observability.yaml up -d
```

### 4. Start All Services

**Option A: Multi-App Run (Recommended)**

```bash
dapr run -f dapr.yaml
```

**Option B: Individual Services in Separate Terminals**

```bash
# Terminal 1 - Kitchen Service
cd kitchen-service
dapr run --app-id kitchen-service --app-port 5002 --dapr-http-port 3502 --resources-path ../components --config ../components/config.yaml -- python app.py

# Terminal 2 - Bar Service
cd bar-service
dapr run --app-id bar-service --app-port 5003 --dapr-http-port 3503 --resources-path ../components --config ../components/config.yaml -- python app.py

# Terminal 3 - Order Service (Frontend)
cd order-service
dapr run --app-id order-service --app-port 5001 --dapr-http-port 3501 --resources-path ../components --config ../components/config.yaml -- python app.py
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

## Kubernetes Deployment with DevSpace

Run this demo in Kubernetes using DevSpace for a production-like environment with hot-reloading!

### Prerequisites

- Kubernetes cluster (minikube, kind, Docker Desktop, or remote cluster)
- [DevSpace CLI](https://devspace.sh/cli/docs/getting-started/installation)
- [Dapr installed on Kubernetes](https://docs.dapr.io/operations/hosting/kubernetes/kubernetes-deploy/)
- kubectl configured to access your cluster

### Setup Dapr on Kubernetes

If Dapr isn't installed on your cluster yet:

```bash
# Install Dapr on your cluster
dapr init -k

# Verify installation
dapr status -k
```

### Deploy with DevSpace

Uses **Cloud Native Buildpacks** - no Dockerfiles needed! The buildpacks auto-detect your Python apps.

```bash
# Quick start with helper script
./run-k8s.sh

# Or run directly:
# Development mode with hot-reload (recommended)
devspace dev

# Or just deploy without dev mode
devspace deploy
```

### What DevSpace Does

When you run `devspace dev`:
- Builds container images using **Cloud Native Buildpacks** (no Dockerfile required!)
- Deploys Redis to your cluster via Helm
- Deploys all Dapr components (state store, pub/sub, config)
- Deploys all three microservices with Dapr sidecars
- Sets up port forwarding (access via localhost:5001)
- Syncs code changes in real-time for hot-reloading
- Streams logs from all services

### Access the Application

Once deployed, DevSpace automatically forwards ports:

- **Order Service (Frontend)**: http://localhost:5001
- Check logs: `devspace logs` or see them in the dev terminal

### Stop and Clean Up

```bash
# Stop dev mode (Ctrl+C in terminal)

# Purge all deployments
devspace purge
```

### Development Workflow

```bash
# Start development mode
devspace dev

# Make changes to any service code
# DevSpace automatically syncs files and restarts the app

# View logs
devspace logs -f

# Open a shell in a running container
devspace enter
```

### Kubernetes-Specific Files

- [devspace.yaml](devspace.yaml) - DevSpace configuration with Buildpacks
- [k8s/](k8s/) - Kubernetes manifests for all services
- [components-k8s/](components-k8s/) - Dapr components configured for Kubernetes
- [KUBERNETES.md](KUBERNETES.md) - Detailed Kubernetes deployment guide
- [run-k8s.sh](run-k8s.sh) - Helper script for easy deployment

### Why DevSpace + Buildpacks?

- **No Dockerfiles needed**: Cloud Native Buildpacks auto-detect Python and build optimized images
- **Fast iteration**: Code changes sync instantly, no rebuild/redeploy
- **Production-like**: Run in real Kubernetes with Dapr
- **Multi-service**: Manage all 3 services from one command
- **Works everywhere**: Local k8s (kind/minikube) or remote clusters
- **Best practices**: Buildpacks include security updates and optimizations

## Next Steps

Want to extend this demo? Try:

- Add workflow orchestration for order completion
- Implement service-to-service invocation
- Add observability with Zipkin tracing in Kubernetes
- Add secrets management for API keys
- Implement resiliency policies (retries, circuit breakers)
- Deploy to a cloud Kubernetes service (AKS, EKS, GKE)

## Troubleshooting

**Services not communicating?**
- Check Redis is running: `redis-cli ping`
- Verify Dapr is initialized: `dapr --version`
- Check components path is correct

**Port conflicts?**
- Change app ports in run scripts
- Ensure Dapr HTTP ports are unique per service

Enjoy your burger and beer! 🍔🍺
