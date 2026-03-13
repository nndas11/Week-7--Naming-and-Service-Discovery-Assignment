#!/bin/bash

# Quick Demo Script for Service Registry
# This script demonstrates the service registry in action

echo "=========================================="
echo "Service Registry Quick Demo"
echo "=========================================="
echo ""

# Check if Flask is installed
if ! python3 -c "import flask" 2>/dev/null; then
    echo "❌ Flask not installed. Installing dependencies..."
    pip3 install -r requirements.txt
    echo ""
fi

echo "📋 This demo will:"
echo "   1. Start the service registry"
echo "   2. Register two services"
echo "   3. Demonstrate service discovery"
echo "   4. Show heartbeat mechanism"
echo ""
echo "Press Ctrl+C to stop at any time"
echo ""
read -p "Press Enter to continue..."

# Start registry in background
echo ""
echo "🚀 Starting Service Registry..."
python3 service_registry_improved.py > /tmp/registry.log 2>&1 &
REGISTRY_PID=$!
echo "   Registry PID: $REGISTRY_PID"

# Wait for registry to start
sleep 2

# Check if registry is running
if ! curl -s http://localhost:5001/health > /dev/null; then
    echo "❌ Failed to start registry. Check /tmp/registry.log"
    kill $REGISTRY_PID 2>/dev/null
    exit 1
fi

echo "✅ Registry is running on http://localhost:5001"
echo ""

# Register first service
echo "📝 Registering cart-service..."
curl -s -X POST http://localhost:5001/register \
  -H "Content-Type: application/json" \
  -d '{"service": "cart-service", "address": "http://localhost:8001"}' | python3 -m json.tool
echo ""

# Register second service
echo "📝 Registering payment-service..."
curl -s -X POST http://localhost:5001/register \
  -H "Content-Type: application/json" \
  -d '{"service": "payment-service", "address": "http://localhost:8002"}' | python3 -m json.tool
echo ""

# Register another instance of cart-service
echo "📝 Registering another cart-service instance..."
curl -s -X POST http://localhost:5001/register \
  -H "Content-Type: application/json" \
  -d '{"service": "cart-service", "address": "http://localhost:8003"}' | python3 -m json.tool
echo ""

# List all services
echo "📋 Listing all registered services..."
curl -s http://localhost:5001/services | python3 -m json.tool
echo ""

# Discover cart-service
echo "🔍 Discovering cart-service instances..."
curl -s http://localhost:5001/discover/cart-service | python3 -m json.tool
echo ""

# Send heartbeat
echo "💓 Sending heartbeat for cart-service..."
curl -s -X POST http://localhost:5001/heartbeat \
  -H "Content-Type: application/json" \
  -d '{"service": "cart-service", "address": "http://localhost:8001"}' | python3 -m json.tool
echo ""

# Wait and show stale service cleanup
echo "⏳ Waiting 35 seconds to demonstrate stale service cleanup..."
echo "   (Services without heartbeats will be removed)"
for i in {35..1}; do
    echo -ne "   $i seconds remaining...\r"
    sleep 1
done
echo ""

echo "🔍 Checking services after timeout..."
curl -s http://localhost:5001/discover/cart-service | python3 -m json.tool
echo ""
echo "   Notice: Services without heartbeats have been removed!"
echo ""

# Cleanup
echo "🧹 Cleaning up..."
kill $REGISTRY_PID 2>/dev/null
echo "✅ Demo complete!"
echo ""
echo "=========================================="
echo "Next Steps:"
echo "=========================================="
echo "1. Read README.md for detailed documentation"
echo "2. Read LEARNING_GUIDE.md for in-depth explanations"
echo "3. Try running: python3 service_registry_improved.py"
echo "4. In another terminal: python3 example_service.py user-service 8001"
echo "5. Experiment with the API endpoints!"
echo ""

# Made with Bob
