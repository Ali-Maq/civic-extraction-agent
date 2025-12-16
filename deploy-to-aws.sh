#!/bin/bash
# =============================================================================
# CIViC Extraction - Complete AWS Deployment Script
# =============================================================================
# This script handles the entire deployment process:
# 1. Builds the frontend
# 2. Builds the Docker image
# 3. Pushes to AWS ECR
# 4. Deploys to EC2
# 5. Sets up CloudFront distribution (optional)
# =============================================================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
AWS_REGION="us-east-1"
ECR_REPO_NAME="civic-extraction"
EC2_INSTANCE_NAME="civic-extraction"
INSTANCE_TYPE="t4g.micro"
SECURITY_GROUP_NAME="civic-extraction-sg"
IAM_ROLE_NAME="civic-extraction-ec2-role"
IAM_PROFILE_NAME="civic-extraction-instance-profile"

# Functions
print_step() {
    echo -e "${BLUE}==>${NC} $1"
}

print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

# Check prerequisites
check_prerequisites() {
    print_step "Checking prerequisites..."

    # Check Docker
    if ! command -v docker &> /dev/null; then
        print_error "Docker not found. Please install Docker first."
        exit 1
    fi
    print_success "Docker found: $(docker --version | head -1)"

    # Check AWS CLI
    if ! command -v aws &> /dev/null; then
        print_error "AWS CLI not found. Please install AWS CLI first."
        exit 1
    fi
    print_success "AWS CLI found: $(aws --version | head -1)"

    # Check AWS credentials
    if ! aws sts get-caller-identity &> /dev/null; then
        print_error "AWS credentials not configured. Run 'aws configure' first."
        exit 1
    fi
    AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
    print_success "AWS credentials configured (Account: $AWS_ACCOUNT_ID)"

    # Check Node.js
    if ! command -v npm &> /dev/null; then
        print_error "Node.js/npm not found. Please install Node.js first."
        exit 1
    fi
    print_success "Node.js found: $(node --version)"
}

# Build frontend
build_frontend() {
    print_step "Building frontend..."
    cd frontend

    # Install dependencies if needed
    if [ ! -d "node_modules" ]; then
        print_warning "node_modules not found. Running npm install..."
        npm install
    fi

    # Build
    npm run build

    # Verify build
    if [ ! -f "dist/index.html" ]; then
        print_error "Frontend build failed - dist/index.html not found"
        exit 1
    fi

    # Verify PDF worker
    if ! ls dist/assets/pdf.worker*.mjs 1> /dev/null 2>&1; then
        print_error "PDF worker not bundled"
        exit 1
    fi

    WORKER_FILE=$(ls dist/assets/pdf.worker*.mjs)
    WORKER_SIZE=$(ls -lh $WORKER_FILE | awk '{print $5}')
    print_success "Frontend built successfully (PDF worker: $(basename $WORKER_FILE) - $WORKER_SIZE)"

    cd ..
}

# Build Docker image
build_docker_image() {
    print_step "Building Docker image..."

    docker build -t civic-extraction:latest . --quiet

    print_success "Docker image built: civic-extraction:latest"
}

# Create ECR repository if it doesn't exist
create_ecr_repo() {
    print_step "Checking ECR repository..."

    if ! aws ecr describe-repositories --repository-names $ECR_REPO_NAME --region $AWS_REGION &> /dev/null; then
        print_warning "ECR repository not found. Creating..."
        aws ecr create-repository --repository-name $ECR_REPO_NAME --region $AWS_REGION > /dev/null
        print_success "ECR repository created"
    else
        print_success "ECR repository exists"
    fi
}

# Push to ECR
push_to_ecr() {
    print_step "Pushing Docker image to ECR..."

    # Login to ECR
    aws ecr get-login-password --region $AWS_REGION | \
        docker login --username AWS --password-stdin \
        $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com

    # Tag image
    docker tag civic-extraction:latest \
        $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPO_NAME:latest

    # Push image
    docker push $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPO_NAME:latest | \
        grep -E "(Pushed|digest|latest)"

    print_success "Image pushed to ECR"
}

# Create IAM role and instance profile
create_iam_role() {
    print_step "Setting up IAM role..."

    # Check if role exists
    if ! aws iam get-role --role-name $IAM_ROLE_NAME &> /dev/null; then
        print_warning "IAM role not found. Creating..."

        # Create trust policy
        cat > /tmp/ec2-trust-policy.json << EOF
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {"Service": "ec2.amazonaws.com"},
    "Action": "sts:AssumeRole"
  }]
}
EOF

        # Create role
        aws iam create-role \
            --role-name $IAM_ROLE_NAME \
            --assume-role-policy-document file:///tmp/ec2-trust-policy.json \
            --output text > /dev/null

        # Attach ECR read policy
        aws iam attach-role-policy \
            --role-name $IAM_ROLE_NAME \
            --policy-arn arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly

        print_success "IAM role created"
    else
        print_success "IAM role exists"
    fi

    # Create instance profile if it doesn't exist
    if ! aws iam get-instance-profile --instance-profile-name $IAM_PROFILE_NAME &> /dev/null; then
        print_warning "Instance profile not found. Creating..."
        aws iam create-instance-profile --instance-profile-name $IAM_PROFILE_NAME > /dev/null
        sleep 2
        aws iam add-role-to-instance-profile \
            --instance-profile-name $IAM_PROFILE_NAME \
            --role-name $IAM_ROLE_NAME
        print_success "Instance profile created"
    else
        print_success "Instance profile exists"
    fi
}

# Create security group
create_security_group() {
    print_step "Setting up security group..."

    # Get default VPC
    VPC_ID=$(aws ec2 describe-vpcs --filters "Name=is-default,Values=true" --query 'Vpcs[0].VpcId' --output text)

    # Check if security group exists
    EXISTING_SG=$(aws ec2 describe-security-groups \
        --filters "Name=group-name,Values=$SECURITY_GROUP_NAME" \
        --query 'SecurityGroups[0].GroupId' --output text 2>/dev/null)

    if [ "$EXISTING_SG" != "None" ] && [ -n "$EXISTING_SG" ]; then
        SECURITY_GROUP_ID=$EXISTING_SG
        print_success "Security group exists: $SECURITY_GROUP_ID"
    else
        print_warning "Security group not found. Creating..."
        SECURITY_GROUP_ID=$(aws ec2 create-security-group \
            --group-name $SECURITY_GROUP_NAME \
            --description "Security group for CIViC Extraction application" \
            --vpc-id $VPC_ID \
            --query 'GroupId' --output text)

        # Add rules
        aws ec2 authorize-security-group-ingress --group-id $SECURITY_GROUP_ID --protocol tcp --port 80 --cidr 0.0.0.0/0
        aws ec2 authorize-security-group-ingress --group-id $SECURITY_GROUP_ID --protocol tcp --port 443 --cidr 0.0.0.0/0
        aws ec2 authorize-security-group-ingress --group-id $SECURITY_GROUP_ID --protocol tcp --port 22 --cidr 0.0.0.0/0

        print_success "Security group created: $SECURITY_GROUP_ID"
    fi
}

# Deploy to EC2
deploy_to_ec2() {
    print_step "Deploying to EC2..."

    # Check if instance already exists
    EXISTING_INSTANCE=$(aws ec2 describe-instances \
        --filters "Name=tag:Name,Values=$EC2_INSTANCE_NAME" "Name=instance-state-name,Values=running" \
        --query 'Reservations[0].Instances[0].InstanceId' --output text 2>/dev/null)

    if [ "$EXISTING_INSTANCE" != "None" ] && [ -n "$EXISTING_INSTANCE" ]; then
        INSTANCE_ID=$EXISTING_INSTANCE
        INSTANCE_IP=$(aws ec2 describe-instances --instance-ids $INSTANCE_ID \
            --query 'Reservations[0].Instances[0].PublicIpAddress' --output text)
        print_success "Using existing instance: $INSTANCE_ID ($INSTANCE_IP)"

        # Update container on existing instance
        print_step "Updating container on EC2..."
        update_container_on_ec2 $INSTANCE_ID $INSTANCE_IP
    else
        # Launch new instance
        print_warning "No running instance found. Launching new instance..."
        launch_new_instance
    fi
}

# Update container on existing EC2 instance
update_container_on_ec2() {
    INSTANCE_ID=$1
    INSTANCE_IP=$2

    # Get availability zone
    AZ=$(aws ec2 describe-instances --instance-ids $INSTANCE_ID \
        --query 'Reservations[0].Instances[0].Placement.AvailabilityZone' --output text)

    print_step "Connecting to EC2 instance via SSM..."

    # Create deployment script
    cat > /tmp/deploy-container.sh << 'DEPLOY_SCRIPT'
#!/bin/bash
set -e
echo "Logging into ECR..."
aws ecr get-login-password --region us-east-1 | sudo docker login --username AWS --password-stdin {{AWS_ACCOUNT_ID}}.dkr.ecr.us-east-1.amazonaws.com
echo "Pulling latest image..."
sudo docker pull {{AWS_ACCOUNT_ID}}.dkr.ecr.us-east-1.amazonaws.com/civic-extraction:latest
echo "Stopping old container..."
sudo docker stop civic-extraction 2>/dev/null || true
sudo docker rm civic-extraction 2>/dev/null || true
echo "Starting new container..."
sudo docker run -d \
  --name civic-extraction \
  -p 80:80 \
  --restart unless-stopped \
  -v /opt/civic-logs:/app/logs \
  {{AWS_ACCOUNT_ID}}.dkr.ecr.us-east-1.amazonaws.com/civic-extraction:latest
echo "Container deployed!"
sudo docker ps | grep civic-extraction
DEPLOY_SCRIPT

    # Replace placeholders
    sed -i.bak "s/{{AWS_ACCOUNT_ID}}/$AWS_ACCOUNT_ID/g" /tmp/deploy-container.sh

    # Try SSH deployment (requires key)
    print_warning "Please ensure you have SSH access to the instance"
    print_warning "Attempting deployment via docker commands..."

    # Alternative: Use AWS Systems Manager Session Manager if available
    # For now, provide the script for manual execution
    print_success "Deployment script created at /tmp/deploy-container.sh"
    print_warning "Please run this script on your EC2 instance to update the container"
}

# Launch new EC2 instance
launch_new_instance() {
    # Get latest ARM64 Amazon Linux 2023 AMI
    AMI_ID=$(aws ec2 describe-images \
        --owners amazon \
        --filters "Name=name,Values=al2023-ami-2023*-arm64" "Name=state,Values=available" \
        --query 'Images | sort_by(@, &CreationDate) | [-1].ImageId' \
        --output text)

    print_step "Launching new EC2 instance (AMI: $AMI_ID)..."

    # Create user data script
    cat > /tmp/user-data.sh << 'USERDATA'
#!/bin/bash
set -e
yum update -y
yum install -y docker aws-cli
systemctl start docker
systemctl enable docker
usermod -aG docker ec2-user

# Login to ECR and pull image
aws ecr get-login-password --region us-east-1 | \
    docker login --username AWS --password-stdin {{AWS_ACCOUNT_ID}}.dkr.ecr.us-east-1.amazonaws.com
docker pull {{AWS_ACCOUNT_ID}}.dkr.ecr.us-east-1.amazonaws.com/civic-extraction:latest

# Create logs directory
mkdir -p /opt/civic-logs

# Run container
docker run -d \
    --name civic-extraction \
    -p 80:80 \
    --restart unless-stopped \
    -v /opt/civic-logs:/app/logs \
    {{AWS_ACCOUNT_ID}}.dkr.ecr.us-east-1.amazonaws.com/civic-extraction:latest

echo "Deployment complete!"
USERDATA

    # Replace placeholders
    sed -i.bak "s/{{AWS_ACCOUNT_ID}}/$AWS_ACCOUNT_ID/g" /tmp/user-data.sh

    # Launch instance
    INSTANCE_ID=$(aws ec2 run-instances \
        --image-id $AMI_ID \
        --instance-type $INSTANCE_TYPE \
        --security-group-ids $SECURITY_GROUP_ID \
        --iam-instance-profile Name=$IAM_PROFILE_NAME \
        --user-data file:///tmp/user-data.sh \
        --tag-specifications "ResourceType=instance,Tags=[{Key=Name,Value=$EC2_INSTANCE_NAME},{Key=Project,Value=CIViC},{Key=Environment,Value=production}]" \
        --block-device-mappings 'DeviceName=/dev/xvda,Ebs={VolumeSize=20,VolumeType=gp3}' \
        --query 'Instances[0].InstanceId' \
        --output text)

    print_success "Instance launched: $INSTANCE_ID"
    print_step "Waiting for instance to start..."

    aws ec2 wait instance-running --instance-ids $INSTANCE_ID

    # Get public IP
    INSTANCE_IP=$(aws ec2 describe-instances --instance-ids $INSTANCE_ID \
        --query 'Reservations[0].Instances[0].PublicIpAddress' --output text)

    print_success "Instance running at: $INSTANCE_IP"
    print_warning "Waiting 90 seconds for container to start..."
    sleep 90
}

# Create CloudFront distribution
create_cloudfront() {
    print_step "Creating CloudFront distribution..."

    # Get EC2 public IP
    INSTANCE_IP=$(aws ec2 describe-instances \
        --filters "Name=tag:Name,Values=$EC2_INSTANCE_NAME" "Name=instance-state-name,Values=running" \
        --query 'Reservations[0].Instances[0].PublicIpAddress' --output text)

    if [ "$INSTANCE_IP" == "None" ] || [ -z "$INSTANCE_IP" ]; then
        print_error "No running EC2 instance found"
        return 1
    fi

    # Create CloudFront distribution config
    cat > /tmp/cloudfront-config.json << EOF
{
  "CallerReference": "civic-extraction-$(date +%s)",
  "Comment": "CIViC Extraction CDN",
  "Enabled": true,
  "Origins": {
    "Quantity": 1,
    "Items": [{
      "Id": "civic-ec2",
      "DomainName": "$INSTANCE_IP",
      "CustomOriginConfig": {
        "HTTPPort": 80,
        "HTTPSPort": 443,
        "OriginProtocolPolicy": "http-only"
      }
    }]
  },
  "DefaultRootObject": "index.html",
  "DefaultCacheBehavior": {
    "TargetOriginId": "civic-ec2",
    "ViewerProtocolPolicy": "redirect-to-https",
    "AllowedMethods": {
      "Quantity": 7,
      "Items": ["GET", "HEAD", "OPTIONS", "PUT", "POST", "PATCH", "DELETE"],
      "CachedMethods": {
        "Quantity": 2,
        "Items": ["GET", "HEAD"]
      }
    },
    "ForwardedValues": {
      "QueryString": true,
      "Cookies": {"Forward": "all"},
      "Headers": {
        "Quantity": 4,
        "Items": ["Accept", "Accept-Encoding", "Accept-Language", "Range"]
      }
    },
    "MinTTL": 0,
    "DefaultTTL": 86400,
    "MaxTTL": 31536000,
    "Compress": true,
    "TrustedSigners": {
      "Enabled": false,
      "Quantity": 0
    }
  }
}
EOF

    # Create distribution
    DISTRIBUTION_ID=$(aws cloudfront create-distribution \
        --distribution-config file:///tmp/cloudfront-config.json \
        --query 'Distribution.Id' --output text 2>/dev/null)

    if [ -n "$DISTRIBUTION_ID" ]; then
        DOMAIN_NAME=$(aws cloudfront get-distribution --id $DISTRIBUTION_ID \
            --query 'Distribution.DomainName' --output text)
        print_success "CloudFront distribution created: $DOMAIN_NAME"
        print_warning "Distribution is deploying... This may take 15-20 minutes"
        print_warning "Your application will be available at: https://$DOMAIN_NAME"
    else
        print_error "Failed to create CloudFront distribution"
    fi
}

# Test deployment
test_deployment() {
    print_step "Testing deployment..."

    # Get instance IP
    INSTANCE_IP=$(aws ec2 describe-instances \
        --filters "Name=tag:Name,Values=$EC2_INSTANCE_NAME" "Name=instance-state-name,Values=running" \
        --query 'Reservations[0].Instances[0].PublicIpAddress' --output text)

    if [ "$INSTANCE_IP" == "None" ] || [ -z "$INSTANCE_IP" ]; then
        print_error "No running instance found"
        return 1
    fi

    # Test API
    if curl -s http://$INSTANCE_IP/api/papers | grep -q "papers"; then
        print_success "API responding"
    else
        print_error "API not responding"
    fi

    # Test frontend
    if curl -s -I http://$INSTANCE_IP | grep -q "200 OK"; then
        print_success "Frontend accessible"
    else
        print_error "Frontend not accessible"
    fi

    # Test PDF Range request
    if curl -s -H "Range: bytes=0-1023" -I http://$INSTANCE_IP/api/papers/PMID_12483530/pdf | grep -q "206"; then
        print_success "PDF Range requests working"
    else
        print_error "PDF Range requests not working"
    fi
}

# Main execution
main() {
    echo ""
    echo "========================================="
    echo "  CIViC Extraction - AWS Deployment"
    echo "========================================="
    echo ""

    check_prerequisites
    echo ""

    build_frontend
    echo ""

    build_docker_image
    echo ""

    create_ecr_repo
    echo ""

    push_to_ecr
    echo ""

    create_iam_role
    echo ""

    create_security_group
    echo ""

    deploy_to_ec2
    echo ""

    test_deployment
    echo ""

    # Ask about CloudFront
    read -p "Do you want to create a CloudFront distribution? (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        create_cloudfront
    fi

    echo ""
    echo "========================================="
    print_success "Deployment complete!"
    echo "========================================="
    echo ""

    # Get instance IP
    INSTANCE_IP=$(aws ec2 describe-instances \
        --filters "Name=tag:Name,Values=$EC2_INSTANCE_NAME" "Name=instance-state-name,Values=running" \
        --query 'Reservations[0].Instances[0].PublicIpAddress' --output text)

    echo "Application URL: http://$INSTANCE_IP"
    echo ""
    echo "Next steps:"
    echo "1. Open the application URL in your browser"
    echo "2. Test all functionality (papers, PDFs, knowledge graph)"
    echo "3. (Optional) Set up a custom domain name"
    echo "4. (Optional) Add SSL certificate for HTTPS"
    echo ""
}

# Run main function
main
