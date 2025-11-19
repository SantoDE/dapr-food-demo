# Kubernetes Quick Start

## 30-Second Start

```bash
# 1. Start a Kubernetes cluster (choose one):
# - Docker Desktop: Enable in settings
# - minikube start
# - kind create cluster

# 2. Install Dapr on Kubernetes
dapr init -k

# 3. Deploy everything
./run-k8s.sh
```

**That's it!** Open http://localhost:5001

## What Just Happened?

- Built 3 Python services using **Cloud Native Buildpacks** (no Dockerfiles!)
- Deployed Redis to Kubernetes
- Deployed all Dapr components
- Deployed order-service, kitchen-service, bar-service
- Each service got a Dapr sidecar automatically
- Port-forwarded 5001 to your machine

## Commands

```bash
# Start dev mode (hot-reload)
devspace dev

# Just deploy
devspace deploy

# View logs
devspace logs -f

# Shell into a container
devspace enter

# Clean up everything
devspace purge
```

## Make Code Changes

1. While `devspace dev` is running
2. Edit any `.py` file in `order-service/`, `kitchen-service/`, or `bar-service/`
3. Save the file
4. DevSpace syncs it automatically
5. Flask reloads
6. Refresh browser - done!

## Troubleshooting

```bash
# Check everything
kubectl get pods
dapr status -k

# See what's wrong with a pod
kubectl describe pod <pod-name>
kubectl logs <pod-name> -c order-service
kubectl logs <pod-name> -c daprd

# Redis problems?
kubectl get pods -l app.kubernetes.io/name=redis

# Start fresh
devspace purge
devspace dev
```

## Files

- **[devspace.yaml](devspace.yaml)** - DevSpace config with Buildpacks
- **[k8s/](k8s/)** - Kubernetes manifests
- **[components-k8s/](components-k8s/)** - Dapr components for k8s
- **[KUBERNETES.md](KUBERNETES.md)** - Full guide
- **[DEPLOYMENT_SUMMARY.md](DEPLOYMENT_SUMMARY.md)** - What was created

## Local vs Kubernetes

| Feature | Local (dapr run -f) | Kubernetes (devspace dev) |
|---------|---------------------|---------------------------|
| Redis | localhost:6379 | redis-master service |
| Containers | No | Yes (via Buildpacks) |
| Dapr sidecars | Separate process | Injected in pod |
| Components | `components/` | `components-k8s/` |
| Access | localhost:5001 | Port-forward to 5001 |
| Use case | Quick dev | Production-realistic |

Happy deploying! 🚀
