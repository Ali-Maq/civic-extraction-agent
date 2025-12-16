# Production Dockerfile for CIViC Evidence Extraction System
# Build frontend locally first: cd frontend && npm install && npm run build

FROM node:18-alpine

# Install nginx and curl for healthcheck
RUN apk add --no-cache nginx curl

# Create app directory
WORKDIR /app

# Copy built frontend (must be built locally first)
COPY frontend/dist /app/frontend/dist

# Copy backend server
COPY frontend/server /app/frontend/server
COPY frontend/package*.json /app/frontend/

# Install production dependencies
WORKDIR /app/frontend
RUN npm install --production && npm cache clean --force

# Copy data and outputs
WORKDIR /app
COPY data /app/data
COPY outputs /app/outputs

# Create logs directory
RUN mkdir -p /app/logs

# Copy nginx configuration
COPY deployment/nginx-docker.conf /etc/nginx/http.d/default.conf

# Expose ports
EXPOSE 80 4177

# Start script
COPY deployment/docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

CMD ["/docker-entrypoint.sh"]
