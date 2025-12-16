# Deployment Scripts and Configuration

This directory contains everything needed to deploy the CIViC Evidence Extraction application to AWS EC2.

## Files Overview

### Configuration Files
- **nginx.conf** - Nginx web server configuration (reverse proxy + static file serving)
- **ecosystem.config.js** - PM2 process manager configuration for the API server

### Deployment Scripts
- **deploy-local.sh** - Build and package the application on your local machine
- **setup-ec2.sh** - Install dependencies and configure the EC2 instance
- **quick-deploy.sh** - One-command deployment (build + upload + setup)
- **monitor.sh** - Health check and monitoring script

## Quick Start (Recommended)

The easiest way to deploy:

```bash
# Make scripts executable (if not already)
chmod +x deployment/*.sh

# One-command deploy
./deployment/quick-deploy.sh YOUR-KEY.pem ubuntu@YOUR-EC2-IP
```

This will:
1. Build the frontend locally
2. Package everything for deployment
3. Upload to EC2
4. Install all dependencies
5. Configure Nginx and PM2
6. Start the application

**Total time:** ~10 minutes

---

## Manual Deployment (Step by Step)

If you prefer more control or need to troubleshoot:

### Step 1: Prepare Locally

```bash
cd deployment
./deploy-local.sh
```

This creates a deployment package: `civic-deployment-YYYYMMDD-HHMMSS.tar.gz`

### Step 2: Upload to EC2

```bash
scp -i YOUR-KEY.pem civic-deployment-*.tar.gz ubuntu@YOUR-EC2-IP:~/
```

### Step 3: Extract on EC2

```bash
ssh -i YOUR-KEY.pem ubuntu@YOUR-EC2-IP

# Create application directory
sudo mkdir -p /opt/civic-extraction
sudo chown ubuntu:ubuntu /opt/civic-extraction

# Extract package
cd /opt/civic-extraction
tar -xzf ~/civic-deployment-*.tar.gz
```

### Step 4: Run Setup

```bash
cd /opt/civic-extraction/deployment
bash setup-ec2.sh
```

This will:
- Update system packages
- Install Node.js 18, Nginx, and PM2
- Configure Nginx as reverse proxy
- Start the API with PM2
- Enable auto-start on reboot

---

## Post-Deployment

### Access Your Application

```bash
# Get your EC2 public IP
curl http://169.254.169.254/latest/meta-data/public-ipv4
```

Open in browser: `http://YOUR-EC2-IP`

### Verify Everything Works

```bash
# Check PM2 status
pm2 status

# View API logs
pm2 logs civic-api

# Check Nginx status
sudo systemctl status nginx

# View Nginx logs
sudo tail -f /var/log/nginx/civic-extraction-access.log
```

### Set Up SSL (Optional but Recommended)

If you have a domain name:

```bash
# Install Certbot
sudo apt install -y certbot python3-certbot-nginx

# Get SSL certificate
sudo certbot --nginx -d your-domain.com

# Auto-renewal is configured automatically
# Test renewal: sudo certbot renew --dry-run
```

---

## Common Commands

### Application Management

```bash
# Restart API
pm2 restart civic-api

# Stop API
pm2 stop civic-api

# View logs
pm2 logs civic-api

# Monitor resources
pm2 monit

# Clear logs
pm2 flush
```

### Nginx Management

```bash
# Test configuration
sudo nginx -t

# Restart Nginx
sudo systemctl restart nginx

# View access logs
sudo tail -f /var/log/nginx/civic-extraction-access.log

# View error logs
sudo tail -f /var/log/nginx/civic-extraction-error.log
```

### System Monitoring

```bash
# Check disk space
df -h

# Check memory usage
free -h

# Check CPU usage
top

# Check running processes
ps aux | grep node
```

---

## Updating the Application

### Update Frontend Only

```bash
# On local machine: rebuild frontend
cd frontend
npm run build

# Upload just the dist folder
scp -i YOUR-KEY.pem -r dist ubuntu@YOUR-EC2-IP:/opt/civic-extraction/frontend/

# No restart needed (Nginx serves static files)
```

### Update API

```bash
# On local machine: package server files
cd frontend
tar -czf server.tar.gz server/

# Upload
scp -i YOUR-KEY.pem server.tar.gz ubuntu@YOUR-EC2-IP:~/

# On EC2: extract and restart
ssh -i YOUR-KEY.pem ubuntu@YOUR-EC2-IP
cd /opt/civic-extraction/frontend
tar -xzf ~/server.tar.gz
pm2 restart civic-api
```

### Full Redeployment

Just run the quick-deploy script again:

```bash
./deployment/quick-deploy.sh YOUR-KEY.pem ubuntu@YOUR-EC2-IP
```

---

## Troubleshooting

### Application Won't Start

```bash
# Check PM2 logs
pm2 logs civic-api --lines 100

# Check if port 4177 is available
sudo lsof -i :4177

# Restart PM2
pm2 restart civic-api
```

### Nginx Returns 502 Bad Gateway

```bash
# Check if API is running
pm2 status

# Check Nginx error logs
sudo tail -f /var/log/nginx/civic-extraction-error.log

# Test API directly
curl http://localhost:4177/api/papers
```

### Out of Disk Space

```bash
# Check disk usage
df -h

# Clean up
sudo apt autoremove
sudo apt clean
pm2 flush

# Clear old deployment packages
rm -f ~/civic-deployment-*.tar.gz
```

### Out of Memory

```bash
# Check memory
free -h

# Add swap (if not already configured)
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile

# Make permanent
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

---

## Monitoring Script

Use the included monitoring script:

```bash
# Run health check
./deployment/monitor.sh

# Add to crontab for automatic monitoring (every 5 minutes)
crontab -e
# Add: */5 * * * * /opt/civic-extraction/deployment/monitor.sh
```

---

## Backup

### Manual Backup

```bash
# Backup outputs and data
cd /opt/civic-extraction
tar -czf backup-$(date +%Y%m%d).tar.gz outputs/ data/

# Download to local machine
scp -i YOUR-KEY.pem ubuntu@YOUR-EC2-IP:/opt/civic-extraction/backup-*.tar.gz ./
```

### Automated Backup (Recommended)

```bash
# Create backup script
sudo nano /opt/civic-extraction/backup.sh

# Add to crontab (daily at 2am)
crontab -e
# Add: 0 2 * * * /opt/civic-extraction/backup.sh
```

### EBS Snapshot (Best)

Use AWS Console to create EBS snapshots:
- Go to EC2 > Volumes
- Select your volume
- Actions > Create Snapshot
- Cost: ~$0.05/GB/month

---

## Cost Monitoring

### Check Data Transfer

```bash
# View Nginx access log stats
sudo cat /var/log/nginx/civic-extraction-access.log | \
  awk '{sum+=$10} END {print "Total bytes: " sum " (" sum/1024/1024 " MB)"}'
```

### Estimate Monthly Costs

With t4g.micro:
- Instance: $3.07/month (FREE first year)
- EBS 10GB: $0.80/month (8GB FREE tier)
- Data Transfer: 1GB free, then $0.09/GB
- **Total: $0-5/month**

---

## Security Checklist

After deployment, verify:

- [ ] SSH only accessible from your IP (Security Group)
- [ ] Firewall enabled: `sudo ufw status`
- [ ] Automatic security updates enabled
- [ ] SSL/TLS configured (if using domain)
- [ ] PM2 running as non-root user
- [ ] Regular backups configured
- [ ] CloudWatch monitoring enabled (optional)

---

## Support

For issues or questions:
1. Check the logs: `pm2 logs civic-api`
2. Review the main deployment plan: `../AWS_DEPLOYMENT_PLAN.md`
3. Test API directly: `curl http://localhost:4177/api/papers`

---

## Architecture Diagram

```
Internet
   │
   ▼
┌─────────────────────────┐
│  AWS EC2 (t4g.micro)    │
│  ┌───────────────────┐  │
│  │  Nginx :80/443    │  │ ← Serves static files + reverse proxy
│  └──────────┬────────┘  │
│             ▼            │
│  ┌───────────────────┐  │
│  │  Express :4177    │  │ ← API server (PM2)
│  └──────────┬────────┘  │
│             ▼            │
│  ┌───────────────────┐  │
│  │  File System      │  │ ← JSON files + PDFs
│  │  /opt/civic-...   │  │
│  └───────────────────┘  │
└─────────────────────────┘
```

---

## What Gets Deployed

```
/opt/civic-extraction/
├── frontend/
│   ├── dist/              # React app (static HTML/CSS/JS)
│   ├── server/            # Express API
│   ├── node_modules/      # Production dependencies
│   └── package.json
├── data/
│   └── papers/            # PDF files (~200MB)
├── outputs/               # Extraction results (~500MB)
│   ├── checkpoints/       # Phase outputs
│   └── logs/              # Session logs
├── logs/                  # Application logs
├── deployment/            # Config files
│   ├── nginx.conf
│   ├── ecosystem.config.js
│   └── *.sh scripts
└── ecosystem.config.js    # PM2 config (copied from deployment/)
```

**Total size:** ~800MB-1GB
**Required EBS:** 10GB (leaves room for growth)

---

**Ready to deploy?** Run `./quick-deploy.sh` and you'll be live in 10 minutes!
