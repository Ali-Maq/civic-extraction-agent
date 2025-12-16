#!/bin/bash
# Quick Docker Test Script
# Run this to test the entire system in Docker locally

set -e

echo "🐳 CIViC Extraction Docker Test Script"
echo "======================================"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print status
print_status() {
    echo -e "${GREEN}✓${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

# Check prerequisites
echo "Step 1: Checking prerequisites..."
if ! command -v docker &> /dev/null; then
    print_error "Docker not found. Please install Docker first."
    exit 1
fi
print_status "Docker found: $(docker --version)"

if ! docker compose version &> /dev/null; then
    print_error "docker compose not found. Please install Docker Compose."
    exit 1
fi
print_status "docker compose found: $(docker compose version)"
echo ""

# Build frontend
echo "Step 2: Building frontend..."
cd frontend

if [ ! -d "node_modules" ]; then
    print_warning "node_modules not found. Running npm install..."
    npm install
fi

print_status "Running npm run build..."
npm run build

# Verify worker file
if ls dist/assets/pdf.worker*.mjs 1> /dev/null 2>&1; then
    WORKER_FILE=$(ls dist/assets/pdf.worker*.mjs)
    WORKER_SIZE=$(ls -lh $WORKER_FILE | awk '{print $5}')
    print_status "PDF worker bundled: $(basename $WORKER_FILE) ($WORKER_SIZE)"
else
    print_error "PDF worker file not found in dist/assets/"
    exit 1
fi

# Verify Range request support in production.cjs
if grep -q "Accept-Ranges" server/production.cjs; then
    print_status "Range request support confirmed in production.cjs"
else
    print_error "Range request support NOT found in production.cjs"
    exit 1
fi

cd ..
echo ""

# Clean up old containers
echo "Step 3: Cleaning up old containers..."
docker compose down 2>/dev/null || true
print_status "Old containers removed"
echo ""

# Build Docker image
echo "Step 4: Building Docker image..."
docker build -t civic-extraction:latest .
print_status "Docker image built successfully"
echo ""

# Start container
echo "Step 5: Starting Docker container..."
docker compose up -d
sleep 5  # Wait for container to start
print_status "Container started"
echo ""

# Wait for container to be healthy
echo "Step 6: Waiting for container to be healthy..."
MAX_WAIT=30
COUNTER=0
while [ $COUNTER -lt $MAX_WAIT ]; do
    if docker compose ps | grep -q "healthy"; then
        print_status "Container is healthy"
        break
    fi
    echo -n "."
    sleep 1
    COUNTER=$((COUNTER + 1))
done

if [ $COUNTER -eq $MAX_WAIT ]; then
    print_error "Container failed to become healthy"
    echo "Logs:"
    docker compose logs
    exit 1
fi
echo ""

# Test API endpoint
echo "Step 7: Testing API endpoint..."
if curl -s http://localhost:8080/api/papers | grep -q "papers"; then
    print_status "API endpoint responds correctly"
else
    print_error "API endpoint failed"
    exit 1
fi
echo ""

# Test frontend
echo "Step 8: Testing frontend..."
if curl -s -I http://localhost:8080 | grep -q "200 OK"; then
    print_status "Frontend is accessible"
else
    print_error "Frontend is not accessible"
    exit 1
fi
echo ""

# Test PDF worker file
echo "Step 9: Testing PDF worker accessibility..."
WORKER_URL=$(curl -s http://localhost:8080 | grep -o 'pdf\.worker\.min-[^"]*\.mjs' | head -1)
if [ -n "$WORKER_URL" ]; then
    if curl -s -I "http://localhost:8080/assets/$WORKER_URL" | grep -q "200 OK"; then
        print_status "PDF worker file is accessible"
    else
        print_error "PDF worker file not accessible at /assets/$WORKER_URL"
        exit 1
    fi
else
    print_warning "Could not find PDF worker URL in index.html"
fi
echo ""

# Test Range request support
echo "Step 10: Testing PDF Range request support..."
RANGE_RESPONSE=$(curl -s -I -H "Range: bytes=0-1023" http://localhost:8080/api/papers/PMID_12483530/pdf)
if echo "$RANGE_RESPONSE" | grep -q "206 Partial Content"; then
    print_status "Range requests return 206 Partial Content ✓"
else
    print_error "Range requests NOT working (expected 206, got other status)"
    echo "$RANGE_RESPONSE"
    exit 1
fi

if echo "$RANGE_RESPONSE" | grep -q "Accept-Ranges: bytes"; then
    print_status "Accept-Ranges header present ✓"
else
    print_error "Accept-Ranges header missing"
    exit 1
fi

if echo "$RANGE_RESPONSE" | grep -q "Content-Range:"; then
    print_status "Content-Range header present ✓"
else
    print_error "Content-Range header missing"
    exit 1
fi
echo ""

# Summary
echo "============================================"
echo -e "${GREEN}✓ ALL TESTS PASSED!${NC}"
echo "============================================"
echo ""
echo "Docker container is running at: http://localhost:8080"
echo ""
echo "Next steps:"
echo "  1. Open http://localhost:8080 in your browser"
echo "  2. Test the PDF viewer manually:"
echo "     - Click 'Get Started'"
echo "     - Select a paper"
echo "     - Click 'Original PDF' tab"
echo "     - Verify PDF loads without errors"
echo "  3. Check browser console for:"
echo "     - [PDF] Worker configured"
echo "     - [PDF] Worker ready"
echo "     - [PDF] Loaded successfully"
echo ""
echo "To view logs:"
echo "  docker compose logs -f"
echo ""
echo "To stop container:"
echo "  docker compose down"
echo ""
echo "After manual testing, proceed to AWS deployment:"
echo "  See DOCKER_TEST_AND_DEPLOY.md PHASE 2"
echo ""
