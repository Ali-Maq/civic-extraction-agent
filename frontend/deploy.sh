#!/bin/bash

# Deployment script for EC2
# Usage: ./deploy.sh

set -e

echo "=== EC2 Deployment Script ==="
echo ""

# Check if environment variables are set
if [ -z "$EC2_HOST" ] || [ -z "$EC2_USER" ] || [ -z "$KEY_PATH" ]; then
    echo "Please set the following environment variables:"
    echo "  export EC2_HOST='ec2-xx-xxx-xxx-xxx.compute-1.amazonaws.com'"
    echo "  export EC2_USER='ec2-user'  # or 'ubuntu'"
    echo "  export KEY_PATH='~/.ssh/your-key.pem'"
    echo ""
    echo "Example:"
    echo "  export EC2_HOST='ec2-3-84-123-45.compute-1.amazonaws.com'"
    echo "  export EC2_USER='ec2-user'"
    echo "  export KEY_PATH='~/.ssh/my-key.pem'"
    exit 1
fi

echo "EC2 Host: $EC2_HOST"
echo "EC2 User: $EC2_USER"
echo "SSH Key: $KEY_PATH"
echo ""

# Build the frontend
echo "Step 1: Building frontend..."
npm run build

# Navigate to parent directory
cd ..

# Create deployment tarball
echo "Step 2: Creating deployment package..."
tar -czf deployment.tar.gz \
    --exclude='node_modules' \
    --exclude='__pycache__' \
    --exclude='.git' \
    --exclude='*.pyc' \
    --exclude='.DS_Store' \
    --exclude='tmp_uploads/*' \
    .

# Transfer to EC2
echo "Step 3: Transferring files to EC2..."
scp -i "$KEY_PATH" deployment.tar.gz "$EC2_USER@$EC2_HOST":~/

# SSH and setup
echo "Step 4: Setting up on EC2..."
ssh -i "$KEY_PATH" "$EC2_USER@$EC2_HOST" << 'ENDSSH'
    # Extract files
    echo "Extracting files..."
    mkdir -p ~/civic_extraction
    cd ~/civic_extraction
    tar -xzf ~/deployment.tar.gz
    rm ~/deployment.tar.gz

    # Create necessary directories
    mkdir -p data/papers outputs logs tmp_uploads

    # Install dependencies
    echo "Installing Node.js dependencies..."
    cd frontend
    npm install --production

    # Check if PM2 is installed
    if ! command -v pm2 &> /dev/null; then
        echo "Installing PM2..."
        sudo npm install -g pm2
    fi

    # Restart or start the application
    if pm2 list | grep -q civic-app; then
        echo "Restarting application..."
        pm2 restart civic-app
    else
        echo "Starting application for the first time..."
        pm2 start server/production.cjs --name civic-app
        pm2 save
    fi

    # Show status
    pm2 status
    echo ""
    echo "Deployment complete!"
    echo "Access your app at: http://$EC2_HOST:4177"
ENDSSH

# Cleanup local tarball
rm deployment.tar.gz

echo ""
echo "=== Deployment Complete ==="
echo "Your application is now running on EC2"
echo "URL: http://$EC2_HOST:4177"
echo ""
echo "To view logs: ssh -i $KEY_PATH $EC2_USER@$EC2_HOST 'pm2 logs civic-app'"
echo "To check status: ssh -i $KEY_PATH $EC2_USER@$EC2_HOST 'pm2 status'"
