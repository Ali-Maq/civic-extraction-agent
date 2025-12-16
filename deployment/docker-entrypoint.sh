#!/bin/sh
set -e

echo "Starting CIViC Extraction System..."

# Start API server in background (using production.cjs with Range request support)
cd /app/frontend
DATA_ROOT=/app/data/papers \
OUTPUTS_ROOT=/app/outputs \
LOGS_ROOT=/app/logs \
PORT=4177 \
node server/production.cjs > /app/logs/api.log 2>&1 &

API_PID=$!
echo "API server started (PID: $API_PID)"

# Wait a moment for API to start
sleep 2

# Test API is running
if curl -s http://127.0.0.1:4177/api/papers > /dev/null; then
    echo "API server is responding"
else
    echo "WARNING: API server not responding"
fi

# Start Nginx in foreground
echo "Starting Nginx..."
nginx -g 'daemon off;'
