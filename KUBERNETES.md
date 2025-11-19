# Kubernetes Deployment Guide

This guide will help you deploy the Burger & Beer Order System to Kubernetes using DevSpace.

## Quick Start

### 1. Install Prerequisites

```bash
# Install DevSpace CLI
# macOS
brew install devspace

# Linux/WSL
curl -s -L "https://github.com/loft-sh/devspace/releases/latest" | sed -nE 's!.*"([^"]*devspace-linux-amd64)".*!https://github.com\1!p' | xargs -n 1 curl -L -o devspace && chmod +x devspace && sudo mv devspace /usr/local/bin

# Windows (PowerShell)
md -Force "$Env:APPDATA\devspace"; [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.SecurityProtocolType]'Tls,Tls11,Tls12';
Invoke-WebRequest -UseBasicParsing ((Invoke-WebRequest -URI "https://github.com/loft-sh/devspace/releases/latest" -UseBasicParsing).Content -replace "(?ms).*`"([^`"]*devspace-windows-amd64.exe)`".*","https://github.com/`$1") -o $Env:APPDATA\devspace\devspace.exe;
$env:Path += ";" + $Env:APPDATA + "\devspace";
[Environment]::SetEnvironmentVariable("Path", $env:Path, [System.EnvironmentVariableTarget]::User);
```

### 2. Start a Kubernetes Cluster

Choose one option:

**Option A: Docker Desktop** (Easiest)
```bash
# Enable Kubernetes in Docker Desktop settings
# It's built-in!
```

**Option B: minikube**
```bash
# Install minikube
brew install minikube  # macOS
# or download from https://minikube.sigs.k8s.io/docs/start/

# Start cluster
minikube start
```

**Option C: kind** (Kubernetes in Docker)
```bash
# Install kind
brew install kind  # macOS
# or: go install sigs.k8s.io/kind@latest

# Create cluster
kind create cluster --name dapr-demo
```

### 3. Install Dapr on Kubernetes

```bash
# Initialize Dapr on your cluster
dapr init -k

# Verify installation
dapr status -k

# You should see:
# - dapr-operator
# - dapr-sidecar-injector
# - dapr-sentry
# - dapr-placement-server
```

### 4. Deploy the Application

**Using Cloud Native Buildpacks**

No Dockerfiles needed! Buildpacks auto-detect your Python apps and build optimized container images:

```bash
# Quick start with helper script (recommended)
./run-k8s.sh

# Or run DevSpace directly
devspace dev
```

### 5. Access the Application

DevSpace automatically forwards port 5001 to your local machine:

- Open http://localhost:5001
- Place an order!
- Watch the logs in your terminal

## Development Workflow

### Make Code Changes

While `devspace dev` is running:

1. Edit any Python file in `order-service/`, `kitchen-service/`, or `bar-service/`
2. Save the file
3. DevSpace automatically syncs it to the running container
4. Flask auto-reloads (thanks to development mode)
5. Refresh your browser to see changes

### View Logs

```bash
# All services (in dev mode, automatic)
devspace logs

# Specific service
devspace logs -p order-service

# Follow logs
devspace logs -f
```

### Execute Commands in Pods

```bash
# Open shell in order-service
devspace enter

# Or specify the service
devspace enter -p kitchen-service
```

### Debugging

```bash
# Check Dapr status
dapr status -k

# Check pods
kubectl get pods

# Check Dapr components
kubectl get components

# Describe a pod to see Dapr sidecar
kubectl describe pod -l app=order-service

# View Dapr logs
kubectl logs -l app=order-service -c daprd

# View app logs
kubectl logs -l app=order-service -c order-service
```

## Architecture in Kubernetes

```
┌─────────────────────────────────────────────────┐
│           Kubernetes Cluster                     │
│                                                  │
│  ┌─────────────────────────────────────────┐   │
│  │  Redis (Bitnami Helm Chart)             │   │
│  │  - State Store                          │   │
│  │  - Pub/Sub                              │   │
│  └─────────────────────────────────────────┘   │
│                                                  │
│  ┌──────────────────────────────────────────┐  │
│  │  Order Service Pod                       │  │
│  │  ├─ order-service container              │  │
│  │  └─ daprd sidecar                        │  │
│  └──────────────────────────────────────────┘  │
│                                                  │
│  ┌──────────────────────────────────────────┐  │
│  │  Kitchen Service Pod                     │  │
│  │  ├─ kitchen-service container            │  │
│  │  └─ daprd sidecar                        │  │
│  └──────────────────────────────────────────┘  │
│                                                  │
│  ┌──────────────────────────────────────────┐  │
│  │  Bar Service Pod                         │  │
│  │  ├─ bar-service container                │  │
│  │  └─ daprd sidecar                        │  │
│  └──────────────────────────────────────────┘  │
│                                                  │
└─────────────────────────────────────────────────┘
          ↑
          │ Port Forward (5001)
          │
    ┌─────────────┐
    │   Browser   │
    │ localhost   │
    └─────────────┘
```

## Key Differences from Local Development

### Local (dapr run -f)
- Uses local Redis on `localhost:6379`
- Components in `components/`
- No containers (runs Python directly)
- Components reference `localhost:6379`

### Kubernetes (devspace dev)
- Uses Redis deployed in k8s cluster via Helm
- Components in `components-k8s/`
- Everything runs in containers built with **Cloud Native Buildpacks**
- Dapr sidecars injected automatically
- Port forwarding for access
- Components reference `redis-master.default.svc.cluster.local:6379`

## Common Commands

```bash
# Development mode with hot-reload
devspace dev

# Deploy only (no dev mode)
devspace deploy

# Rebuild images
devspace build

# Purge everything
devspace purge

# Reset and redeploy
devspace purge && devspace dev

# View DevSpace status
devspace list

# View Kubernetes context
kubectl config current-context

# Switch namespace
devspace use namespace <namespace>
```

## Troubleshooting

### Pods Not Starting

```bash
# Check pod status
kubectl get pods

# Describe pod for events
kubectl describe pod <pod-name>

# Check logs
kubectl logs <pod-name> -c <container-name>
```

### Dapr Sidecar Issues

```bash
# Verify Dapr is installed
dapr status -k

# Check if sidecar injector is running
kubectl get pods -n dapr-system

# Verify Dapr annotations on deployment
kubectl get deployment order-service -o yaml | grep dapr.io
```

### Image Pull Errors

If using a local cluster (minikube/kind), you may need to build images in the cluster:

```bash
# For minikube
eval $(minikube docker-env)
devspace build

# For kind
# Images are automatically loaded
```

### Port Forward Not Working

```bash
# Check if port is already in use
lsof -i :5001

# Manually forward
kubectl port-forward svc/order-service 5001:80
```

### Redis Connection Issues

```bash
# Check Redis is running
kubectl get pods -l app.kubernetes.io/name=redis

# Test Redis connection
kubectl run -it --rm redis-test --image=redis --restart=Never -- redis-cli -h redis-master.default.svc.cluster.local ping
```

## Clean Up

### Stop Development Mode

Press `Ctrl+C` in the terminal running `devspace dev`

### Remove All Resources

```bash
# Purge DevSpace deployments
devspace purge

# Or manually delete
kubectl delete deployment order-service kitchen-service bar-service
kubectl delete svc order-service kitchen-service bar-service
helm uninstall redis
kubectl delete -f components-k8s/
```

### Remove Dapr from Cluster

```bash
dapr uninstall -k
```

### Delete Kubernetes Cluster

```bash
# For minikube
minikube delete

# For kind
kind delete cluster --name dapr-demo

# Docker Desktop - disable in settings
```

## Next Steps

- Add ingress for external access (no port forwarding)
- Deploy to a cloud provider (AKS, EKS, GKE)
- Add observability (Jaeger, Prometheus, Grafana)
- Implement horizontal pod autoscaling
- Add production-grade Redis (HA setup)
- Implement GitOps with ArgoCD
- Add security policies (NetworkPolicies, PodSecurityPolicies)

Happy coding! 🚀
