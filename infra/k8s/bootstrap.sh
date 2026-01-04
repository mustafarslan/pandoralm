#!/bin/bash
set -e

# Configuration
CLUSTER_NAME="pandora-local"
KIND_IMAGE="kindest/node:v1.29.2"

echo "🚀 Starting PandoraLM Kubernetes Bootstrap..."

# 1. Create Kind Cluster
if kind get clusters | grep -q "^$CLUSTER_NAME$"; then
    echo "✅ Cluster '$CLUSTER_NAME' already exists."
else
    echo "📦 Creating Kind cluster..."
    cat <<EOF | kind create cluster --name "$CLUSTER_NAME" --image "$KIND_IMAGE" --config=-
kind: Cluster
apiVersion: kind.x-k8s.io/v1alpha4
nodes:
- role: control-plane
  kubeadmConfigPatches:
  - |
    kind: InitConfiguration
    nodeRegistration:
      kubeletExtraArgs:
        node-labels: "ingress-ready=true"
  extraPortMappings:
  - containerPort: 80
    hostPort: 80
    protocol: TCP
  - containerPort: 443
    hostPort: 443
    protocol: TCP
EOF
fi

echo "⏳ Waiting for cluster to be ready..."
kubectl wait --for=condition=Ready nodes --all --timeout=60s

# 2. Install NGINX Ingress Controller
echo "🌐 Installing NGINX Ingress Controller..."
kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/main/deploy/static/provider/kind/deploy.yaml
echo "⏳ Waiting for Ingress Controller..."
kubectl wait --namespace ingress-nginx \
  --for=condition=ready pod \
  --selector=app.kubernetes.io/component=controller \
  --timeout=90s

# 3. Install KEDA
echo "📈 Installing KEDA..."
helm repo add keda https://kedacore.github.io/charts
helm repo update
helm upgrade --install keda keda/keda --namespace keda --create-namespace
echo "⏳ Waiting for KEDA..."
kubectl wait --namespace keda \
  --for=condition=ready pod \
  --selector=app=keda-operator \
  --timeout=90s

# 5. Install Monitoring Stack
echo "🕵️ Installing Observability Stack..."
# Add Prometheus Repo
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo add grafana https://grafana.github.io/helm-charts
helm repo add open-telemetry https://open-telemetry.github.io/opentelemetry-helm-charts
helm repo update

# Note: In the chart, these are dependencies, so `helm dependency build` above handles it.
# We just need to ensure the `monitoring.enabled=true` flag is set (via values.yaml or --set)

# 6. Deploy PandoraLM
echo "🔮 Deploying PandoraLM Stack..."
# Build dependencies (including monitoring)
cd ../../charts/pandora-os
helm dependency build

# Install/Upgrade Chart
helm upgrade --install pandora . \
    --namespace pandora \
    --create-namespace \
    --set global.env=development \
    --set minio.persistence.enabled=false \
    --set keda.enabled=true \
    --set monitoring.enabled=true

echo "✅ Deployment initiated!"
echo "Check status with: kubectl get pods -n pandora"
echo "Access UI at: http://pandora.local"
echo "Access Grafana at: http://pandora-grafana.local (requires port-forward or Ingress)"
