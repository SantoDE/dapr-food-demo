#!/bin/bash
set -e

SERVICE_NAME=$1
SERVICE_PATH=$2

if [ -z "$SERVICE_NAME" ] || [ -z "$SERVICE_PATH" ]; then
    echo "Usage: $0 <service-name> <service-path>"
    exit 1
fi

echo "Building $SERVICE_NAME with buildpacks..."

pushd "$SERVICE_PATH" > /dev/null

# Use explicit Python buildpack since auto-detection has issues
# --docker-host inherit uses the current DOCKER_HOST from environment
# Disable cache volumes to avoid corruption issues
pack build dapr-food-demo/$SERVICE_NAME \
    --builder paketobuildpacks/builder:base \
    --buildpack paketo-buildpacks/python \
    --docker-host inherit 

popd > /dev/null

echo "✅ Successfully built dapr-food-demo/$SERVICE_NAME"
