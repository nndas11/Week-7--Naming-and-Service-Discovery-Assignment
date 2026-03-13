#!/bin/bash

# Service Registry Minikube Deployment Script

set -e

echo "=========================================="
echo "Service Registry - Minikube Deployment"
echo "=========================================="
echo ""

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if minikube is installed
if ! command -v minikube &> /dev/null; then
    echo -e "${YELLOW}⚠️  Minikube not found. Please install it first:${NC}"
    echo "   https://minikube.sigs.k8s.io/docs/start/"
    exit 1
fi

# Check if kubectl is installed
if ! command -v kubectl &> /dev/null; then
    echo -e "${YELLOW}⚠️  kubectl not found. Please install it first:${NC}"
    echo "   https://kubernetes.io/docs/tasks/tools/"
    exit 1
fi

# Start Minikube if not running
echo -e "${BLUE}1. Checking Minikube status...${NC}"
if ! minikube status &> /dev/null; then
    echo "   Starting Minikube..."
    minikube start
else
    echo -e "   ${GREEN}✓${NC} Minikube is running"
fi
echo ""

# Point Docker to Minikube
echo -e "${BLUE}2. Configuring Docker environment...${NC}"
eval $(minikube docker-env)
echo -e "   ${GREEN}✓${NC} Docker configured to use Minikube"
echo ""

# Build Docker image
echo -e "${BLUE}3. Building Docker image...${NC}"
docker build -t service-registry:latest .
echo -e "   ${GREEN}✓${NC} Image built successfully"
echo ""

# Deploy registry
echo -e "${BLUE}4. Deploying Service Registry...${NC}"
kubectl apply -f k8s/registry-deployment.yaml
echo -e "   ${GREEN}✓${NC} Registry deployed"
echo ""

# Wait for registry to be ready
echo -e "${BLUE}5. Waiting for registry to be ready...${NC}"
kubectl wait --for=condition=ready pod -l app=service-registry --timeout=60s
echo -e "   ${GREEN}✓${NC} Registry is ready"
echo ""

# Deploy example services
echo -e "${BLUE}6. Deploying example services...${NC}"
kubectl apply -f k8s/example-service-deployment.yaml
echo -e "   ${GREEN}✓${NC} Services deployed"
echo ""

# Wait for services to be ready
echo -e "${BLUE}7. Waiting for services to be ready...${NC}"
kubectl wait --for=condition=ready pod -l app=cart-service --timeout=60s
kubectl wait --for=condition=ready pod -l app=payment-service --timeout=60s
echo -e "   ${GREEN}✓${NC} All services are ready"
echo ""

# Get Minikube IP
MINIKUBE_IP=$(minikube ip)

echo "=========================================="
echo -e "${GREEN}✅ Deployment Complete!${NC}"
echo "=========================================="
echo ""
echo "📊 Cluster Status:"
kubectl get pods
echo ""
echo "🌐 Access the Registry:"
echo "   External: http://$MINIKUBE_IP:30001"
echo "   Or use port-forward: kubectl port-forward service/service-registry 5001:5001"
echo ""
echo "🧪 Test Commands:"
echo "   # Health check"
echo "   curl http://$MINIKUBE_IP:30001/health"
echo ""
echo "   # List services"
echo "   curl http://$MINIKUBE_IP:30001/services"
echo ""
echo "   # Discover cart-service"
echo "   curl http://$MINIKUBE_IP:30001/discover/cart-service"
echo ""
echo "📝 View Logs:"
echo "   kubectl logs -l app=service-registry -f"
echo "   kubectl logs -l app=cart-service -f"
echo ""
echo "🧹 Cleanup:"
echo "   kubectl delete -f k8s/"
echo "   minikube stop"
echo ""

# Made with Bob
