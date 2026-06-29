#!/usr/bin/env bash
set -e

CLUSTER_NAME="cns-munich"
REGISTRY_NAME="registry.localhost"
REGISTRY_PORT="5111"

echo "🍔🍺 Burger & Beer Order System - Kubernetes Deployment"
echo "========================================================"
echo ""

# Color codes
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Check required tools
for cmd in devspace kubectl k3d dapr; do
    if ! command -v $cmd &> /dev/null; then
        echo -e "${RED}❌ $cmd not found! Please install it first.${NC}"
        exit 1
    fi
done
echo -e "${GREEN}✅ All required tools found${NC}"

# Ensure k3d registry exists
echo ""
echo "Checking k3d registry..."
if ! k3d registry list | grep -q "$REGISTRY_NAME"; then
    echo -e "${YELLOW}⚠️  Registry not found, creating...${NC}"
    k3d registry create "$REGISTRY_NAME" --port "$REGISTRY_PORT"
    echo -e "${GREEN}✅ Registry created at k3d-${REGISTRY_NAME}:${REGISTRY_PORT}${NC}"
else
    echo -e "${GREEN}✅ Registry k3d-${REGISTRY_NAME}:${REGISTRY_PORT} exists${NC}"
fi

# Ensure k3d cluster exists and is connected to registry
echo ""
echo "Checking k3d cluster..."
if ! k3d cluster list | grep -q "$CLUSTER_NAME"; then
    echo -e "${YELLOW}⚠️  Cluster '${CLUSTER_NAME}' not found, creating...${NC}"
    k3d cluster create "$CLUSTER_NAME" \
        --registry-use "k3d-${REGISTRY_NAME}:${REGISTRY_PORT}" \
        --port "80:80@loadbalancer" \
        --wait
    echo -e "${GREEN}✅ Cluster '${CLUSTER_NAME}' created (external IP: ${VM_IP:-unknown})${NC}"
else
    echo -e "${GREEN}✅ Cluster '${CLUSTER_NAME}' exists${NC}"
fi

# Check if Dapr is installed on k8s
echo ""
echo "Checking Dapr installation on Kubernetes..."
if ! kubectl get namespace dapr-system &> /dev/null; then
    echo -e "${YELLOW}⚠️  Dapr not found, installing...${NC}"
    dapr init -k --dev
    echo -e "${GREEN}✅ Dapr installed${NC}"
else
    echo -e "${GREEN}✅ Dapr found${NC}"
fi

CONTEXT=$(kubectl config current-context)
echo ""
echo -e "${BLUE}Kubernetes Context: ${CONTEXT}${NC}"

# Ask which mode
echo ""
echo "Choose deployment mode:"
echo "  1) Development mode with hot-reload (devspace dev)"
echo "  2) Deploy only (devspace deploy)"
echo ""
read -p "Enter choice [1-2] (default: 2): " CHOICE
CHOICE=${CHOICE:-2}

case $CHOICE in
    1)
        echo ""
        echo -e "${GREEN}Starting development mode...${NC}"
        echo "Press Ctrl+C to stop"
        echo ""
        devspace dev
        ;;
    2)
        echo ""
        echo -e "${GREEN}Deploying to Kubernetes...${NC}"
        devspace deploy
        echo ""
        echo -e "${GREEN}✅ Deployment complete!${NC}"
        echo ""
        VM_IP=$(ip route get 1.1.1.1 2>/dev/null | awk '{print $7; exit}')
        echo "Access the application at:"
        echo "  From this VM: http://localhost"
        if [ -n "$VM_IP" ]; then
            echo "  From your Mac: http://${VM_IP}"
        fi
        ;;
    *)
        echo -e "${RED}Invalid choice${NC}"
        exit 1
        ;;
esac
