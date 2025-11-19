#!/bin/bash
set -e

echo "🍔🍺 Burger & Beer Order System - Kubernetes Deployment"
echo "========================================================"
echo ""

# Color codes
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check if DevSpace is installed
if ! command -v devspace &> /dev/null; then
    echo -e "${RED}❌ DevSpace CLI not found!${NC}"
    echo ""
    echo "Please install DevSpace:"
    echo "  macOS:   brew install devspace"
    echo "  Linux:   curl -s -L 'https://github.com/loft-sh/devspace/releases/latest' | sed -nE 's!.*\"([^\"]*devspace-linux-amd64)\".*!https://github.com\1!p' | xargs -n 1 curl -L -o devspace && chmod +x devspace && sudo mv devspace /usr/local/bin"
    echo ""
    echo "Or visit: https://devspace.sh/cli/docs/getting-started/installation"
    exit 1
fi

# Check if kubectl is available
if ! command -v kubectl &> /dev/null; then
    echo -e "${RED}❌ kubectl not found!${NC}"
    echo "Please install kubectl and configure access to a Kubernetes cluster."
    exit 1
fi

# Check if we can connect to a cluster
if ! kubectl cluster-info &> /dev/null; then
    echo -e "${RED}❌ Cannot connect to Kubernetes cluster!${NC}"
    echo ""
    echo "Please ensure you have a Kubernetes cluster running:"
    echo "  - Docker Desktop (enable in settings)"
    echo "  - minikube start"
    echo "  - kind create cluster"
    exit 1
fi

echo -e "${GREEN}✅ DevSpace CLI found${NC}"
echo -e "${GREEN}✅ kubectl configured${NC}"

# Check if Dapr is installed on k8s
echo ""
echo "Checking Dapr installation on Kubernetes..."
if ! kubectl get namespace dapr-system &> /dev/null; then
    echo -e "${YELLOW}⚠️  Dapr not found on Kubernetes cluster${NC}"
    echo ""
    echo "Installing Dapr on Kubernetes..."

    if ! command -v dapr &> /dev/null; then
        echo -e "${RED}❌ Dapr CLI not found!${NC}"
        echo "Please install Dapr CLI first:"
        echo "  https://docs.dapr.io/getting-started/install-dapr-cli/"
        exit 1
    fi

    dapr init -k --dev
    echo -e "${GREEN}✅ Dapr installed on Kubernetes${NC}"
else
    echo -e "${GREEN}✅ Dapr found on Kubernetes${NC}"
fi

# Get current context
CONTEXT=$(kubectl config current-context)
echo ""
echo -e "${BLUE}Kubernetes Context: ${CONTEXT}${NC}"

# Ask which mode
echo ""
echo "Choose deployment mode:"
echo "  1) Development mode with hot-reload (devspace dev)"
echo "  2) Deploy only (devspace deploy)"
echo ""
read -p "Enter choice [1-2] (default: 1): " CHOICE
CHOICE=${CHOICE:-1}

case $CHOICE in
    1)
        echo ""
        echo -e "${GREEN}Starting development mode with Cloud Native Buildpacks...${NC}"
        echo ""
        echo "This will:"
        echo "  - Build images using Cloud Native Buildpacks (no Dockerfile needed!)"
        echo "  - Deploy all services to Kubernetes with Dapr sidecars"
        echo "  - Set up port forwarding (localhost:5001)"
        echo "  - Watch for code changes and auto-reload"
        echo "  - Stream logs from all services"
        echo ""
        echo "Press Ctrl+C to stop"
        echo ""
        sleep 2
        devspace dev
        ;;
    2)
        echo ""
        echo -e "${GREEN}Deploying to Kubernetes with Buildpacks...${NC}"
        devspace deploy
        echo ""
        echo -e "${GREEN}✅ Deployment complete!${NC}"
        echo ""
        echo "To access the application, run:"
        echo "  kubectl port-forward svc/order-service 5001:80"
        echo ""
        echo "Then open: http://localhost:5001"
        ;;
    *)
        echo -e "${RED}Invalid choice${NC}"
        exit 1
        ;;
esac
