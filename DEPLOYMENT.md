# AWS Deployment Guide

## Current Deployment

**Live Instance:**
- URL: http://13.217.205.13
- Instance ID: i-0df08d1a01b9e8f62
- Instance Type: t4g.micro (ARM64)
- Region: us-east-1
- ECR: AWS_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/civic-extraction

---

## Quick Update

```bash
# 1. Build frontend
cd frontend && npm run build && cd ..

# 2. Build and push Docker image
docker build --platform linux/arm64 -t civic-extraction:latest .
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin AWS_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com
docker tag civic-extraction:latest AWS_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/civic-extraction:latest
docker push AWS_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/civic-extraction:latest

# 3. Update on EC2
ssh -i civic-extraction-key.pem ec2-user@13.217.205.13 << 'EOF'
aws ecr get-login-password --region us-east-1 | sudo docker login --username AWS --password-stdin AWS_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com
sudo docker pull AWS_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/civic-extraction:latest
sudo docker stop civic-extraction
sudo docker rm civic-extraction
sudo docker run -d --name civic-extraction -p 80:80 --restart unless-stopped -v /opt/civic-logs:/app/logs AWS_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/civic-extraction:latest
EOF
```

---

## Fresh Deployment

### Prerequisites
- AWS CLI configured (`aws configure`)
- Docker installed
- Node.js 18+ installed

### Steps

**1. Build Frontend**
```bash
cd frontend
npm install
npm run build
cd ..
```

**2. Create ECR Repository**
```bash
aws ecr create-repository --repository-name civic-extraction --region us-east-1
aws ecr set-repository-policy --repository-name civic-extraction --region us-east-1 --policy-text '{
  "Version": "2012-10-17",
  "Statement": [{
    "Sid": "AllowPull",
    "Effect": "Allow",
    "Principal": "*",
    "Action": [
      "ecr:GetDownloadUrlForLayer",
      "ecr:BatchGetImage",
      "ecr:BatchCheckLayerAvailability"
    ]
  }]
}'
```

**3. Build and Push Docker Image**
```bash
# Build for ARM64 (t4g instances)
docker build --platform linux/arm64 -t civic-extraction:latest .

# Login to ECR
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com

# Tag and push
docker tag civic-extraction:latest ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/civic-extraction:latest
docker push ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/civic-extraction:latest
```

**4. Create IAM Role**
```bash
# Create trust policy
cat > ec2-trust-policy.json << 'EOF'
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
aws iam create-role --role-name civic-extraction-ec2-role --assume-role-policy-document file://ec2-trust-policy.json

# Attach ECR policy
aws iam attach-role-policy --role-name civic-extraction-ec2-role --policy-arn arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly

# Create instance profile
aws iam create-instance-profile --instance-profile-name civic-extraction-instance-profile
aws iam add-role-to-instance-profile --instance-profile-name civic-extraction-instance-profile --role-name civic-extraction-ec2-role
```

**5. Create Security Group**
```bash
# Create security group
aws ec2 create-security-group --group-name civic-extraction-sg --description "CIViC Extraction System" --region us-east-1

# Get security group ID
SG_ID=$(aws ec2 describe-security-groups --group-names civic-extraction-sg --region us-east-1 --query 'SecurityGroups[0].GroupId' --output text)

# Allow HTTP
aws ec2 authorize-security-group-ingress --group-id $SG_ID --protocol tcp --port 80 --cidr 0.0.0.0/0 --region us-east-1

# Allow HTTPS
aws ec2 authorize-security-group-ingress --group-id $SG_ID --protocol tcp --port 443 --cidr 0.0.0.0/0 --region us-east-1

# Allow SSH from your IP
MY_IP=$(curl -s https://checkip.amazonaws.com)
aws ec2 authorize-security-group-ingress --group-id $SG_ID --protocol tcp --port 22 --cidr $MY_IP/32 --region us-east-1
```

**6. Launch EC2 Instance**
```bash
# Find ARM64 AMI
AMI_ID=$(aws ec2 describe-images --owners amazon --filters "Name=name,Values=al2023-ami-2023.*-arm64" "Name=state,Values=available" --region us-east-1 --query 'Images | sort_by(@, &CreationDate) | [-1].ImageId' --output text)

# Create user-data script
cat > user-data.sh << 'EOF'
#!/bin/bash
yum update -y
yum install -y docker
systemctl start docker
systemctl enable docker
usermod -a -G docker ec2-user

# Login to ECR and run container
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com
docker pull ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/civic-extraction:latest
mkdir -p /opt/civic-logs
docker run -d --name civic-extraction -p 80:80 --restart unless-stopped -v /opt/civic-logs:/app/logs ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/civic-extraction:latest
EOF

# Launch instance
aws ec2 run-instances \
  --image-id $AMI_ID \
  --instance-type t4g.micro \
  --security-group-ids $SG_ID \
  --iam-instance-profile Name=civic-extraction-instance-profile \
  --user-data file://user-data.sh \
  --tag-specifications 'ResourceType=instance,Tags=[{Key=Name,Value=civic-extraction}]' \
  --region us-east-1
```

**7. Get Public IP**
```bash
aws ec2 describe-instances --filters "Name=tag:Name,Values=civic-extraction" --query 'Reservations[0].Instances[0].PublicIpAddress' --output text --region us-east-1
```

---

## Monitoring

### View Logs
```bash
ssh -i civic-extraction-key.pem ec2-user@13.217.205.13
sudo docker logs -f civic-extraction
```

### Container Status
```bash
ssh -i civic-extraction-key.pem ec2-user@13.217.205.13
sudo docker ps
sudo docker stats civic-extraction
```

### Restart Container
```bash
ssh -i civic-extraction-key.pem ec2-user@13.217.205.13
sudo docker restart civic-extraction
```

---

## Troubleshooting

### Container Not Running
```bash
# SSH to instance
ssh -i civic-extraction-key.pem ec2-user@13.217.205.13

# Check Docker logs
sudo docker logs civic-extraction

# Check if container exists
sudo docker ps -a | grep civic

# Manually restart
sudo docker stop civic-extraction
sudo docker rm civic-extraction
sudo docker run -d --name civic-extraction -p 80:80 --restart unless-stopped -v /opt/civic-logs:/app/logs AWS_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/civic-extraction:latest
```

### API Not Responding
```bash
# Test locally on EC2
ssh -i civic-extraction-key.pem ec2-user@13.217.205.13
curl http://localhost/api/papers
curl -I http://localhost
```

### Firewall Blocking

Corporate firewalls may block raw IP addresses. Solutions:

1. **Access from outside network** (Recommended)
   - Use personal device/hotspot
   - Access from home network

2. **Set up custom domain**
   - Register domain on Route 53
   - Point A record to EC2 IP

3. **Request IT exception**
   - Contact corporate IT
   - Provide EC2 IP for whitelisting

---

## Cost

**Free Tier (First 12 Months):**
- EC2 t4g.micro: $0/month (750 hours free)
- EBS 20GB: $0/month (30GB free)
- ECR: $0/month (500MB free)
- **Total: $0-2/month**

**After Free Tier:**
- EC2 t4g.micro: $3.07/month
- EBS 20GB gp3: $1.60/month
- ECR: $0.10/month
- **Total: $5-7/month**

---

## Infrastructure Details

### EC2 Instance
- Type: t4g.micro (ARM64)
- AMI: Amazon Linux 2023
- Storage: 20GB gp3
- Region: us-east-1

### Docker Container
- Image: civic-extraction:latest
- Port: 80
- Volumes: /opt/civic-logs
- Restart: unless-stopped

### Services
- Nginx: Port 80 (frontend + proxy)
- Express API: Port 4177 (internal)
- PDF.js Worker: Bundled with frontend

---

**Live Application:** http://13.217.205.13
