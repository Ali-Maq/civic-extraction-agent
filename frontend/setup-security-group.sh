#!/bin/bash

# Script to update EC2 security group to allow traffic
# Usage: ./setup-security-group.sh

set -e

echo "=== EC2 Security Group Setup ==="
echo ""

# Check if environment variables are set
if [ -z "$EC2_HOST" ]; then
    echo "Please set EC2_HOST environment variable:"
    echo "  export EC2_HOST='ec2-xx-xxx-xxx-xxx.compute-1.amazonaws.com'"
    exit 1
fi

echo "EC2 Host: $EC2_HOST"
echo ""

# Get security group ID
echo "Fetching security group ID..."
SG_ID=$(aws ec2 describe-instances \
  --filters "Name=dns-name,Values=$EC2_HOST" \
  --query 'Reservations[0].Instances[0].SecurityGroups[0].GroupId' \
  --output text)

if [ -z "$SG_ID" ] || [ "$SG_ID" = "None" ]; then
    echo "Error: Could not find security group for instance $EC2_HOST"
    echo "Please check:"
    echo "  1. AWS CLI is configured correctly"
    echo "  2. EC2_HOST is correct"
    echo "  3. You have permissions to describe instances"
    exit 1
fi

echo "Security Group ID: $SG_ID"
echo ""

# Function to add rule
add_rule() {
    local port=$1
    local description=$2

    echo "Adding rule for port $port ($description)..."

    if aws ec2 authorize-security-group-ingress \
        --group-id "$SG_ID" \
        --protocol tcp \
        --port "$port" \
        --cidr 0.0.0.0/0 2>/dev/null; then
        echo "✓ Port $port opened successfully"
    else
        echo "⚠ Port $port might already be open (or error occurred)"
    fi
}

# Add rules for common ports
echo "Opening ports..."
echo ""

add_rule 4177 "Application"
echo ""

# Ask about port 80
read -p "Do you want to open port 80 for HTTP (for Nginx)? [y/N]: " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    add_rule 80 "HTTP"
    echo ""
fi

# Ask about port 443
read -p "Do you want to open port 443 for HTTPS? [y/N]: " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    add_rule 443 "HTTPS"
    echo ""
fi

# Show current rules
echo "Current security group rules:"
aws ec2 describe-security-groups \
  --group-ids "$SG_ID" \
  --query 'SecurityGroups[0].IpPermissions[*].[IpProtocol,FromPort,ToPort,IpRanges[0].CidrIp]' \
  --output table

echo ""
echo "=== Setup Complete ==="
echo "Your application should now be accessible at:"
echo "  http://$EC2_HOST:4177"
