# CIViC Evidence Extraction System

Multi-agent genomic evidence extraction pipeline with interactive web interface.

---

## Quick Start (Local Docker)

```bash
# 1. Build and run
docker compose up -d

# 2. Visit
http://localhost:8080

# 3. Stop
docker compose down
```

---

## AWS Deployment

**Current Live Instance:**
- URL: http://13.217.205.13
- Instance: i-0df08d1a01b9e8f62 (t4g.micro, us-east-1)
- Status: ✅ Running

**Update Deployment:**
```bash
# 1. Build frontend
cd frontend
npm run build

# 2. Build Docker image
cd ..
docker build --platform linux/arm64 -t civic-extraction:latest .

# 3. Push to ECR
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin 114288741360.dkr.ecr.us-east-1.amazonaws.com
docker tag civic-extraction:latest 114288741360.dkr.ecr.us-east-1.amazonaws.com/civic-extraction:latest
docker push 114288741360.dkr.ecr.us-east-1.amazonaws.com/civic-extraction:latest

# 4. SSH to EC2 and restart
ssh -i civic-extraction-key.pem ec2-user@13.217.205.13
aws ecr get-login-password --region us-east-1 | sudo docker login --username AWS --password-stdin 114288741360.dkr.ecr.us-east-1.amazonaws.com
sudo docker pull 114288741360.dkr.ecr.us-east-1.amazonaws.com/civic-extraction:latest
sudo docker stop civic-extraction
sudo docker rm civic-extraction
sudo docker run -d --name civic-extraction -p 80:80 --restart unless-stopped -v /opt/civic-logs:/app/logs 114288741360.dkr.ecr.us-east-1.amazonaws.com/civic-extraction:latest
```

---

## System Architecture

```
Internet → AWS EC2 (13.217.205.13)
              ↓
          Docker Container
              ├── Nginx (Port 80)
              │   ├── Frontend (React + PDF.js)
              │   └── Reverse Proxy → API
              └── Express API (Port 4177)
                  ├── /api/papers
                  ├── /api/papers/:id/pdf
                  └── /api/papers/:id/extractions
```

---

## Project Structure

```
civic_extraction_end_to_end/
├── Dockerfile                    # Docker image definition
├── docker-compose.yml            # Local development
├── deployment/
│   ├── docker-entrypoint.sh      # Container startup
│   └── nginx-docker.conf         # Web server config
├── frontend/
│   ├── dist/                     # Built frontend
│   ├── server/production.cjs     # API server (Range requests)
│   └── src/                      # React source code
├── data/papers/                  # PDF files
└── outputs/                      # Extraction results
```

---

## Development

### Frontend Development
```bash
cd frontend
npm install
npm run dev          # Dev server on localhost:5173
npm run build        # Production build
```

### Backend API
```bash
cd frontend
node server/production.cjs    # API on localhost:4177
```

### Docker Testing
```bash
# Build and run
docker compose up -d

# View logs
docker compose logs -f

# Restart
docker compose restart

# Stop and remove
docker compose down
```

---

## Troubleshooting

### Local Docker Issues

**Port already in use:**
```bash
lsof -i :8080
docker compose down
docker compose up -d
```

**Container not starting:**
```bash
docker compose logs
docker ps -a
```

### AWS Deployment Issues

**Check container status:**
```bash
ssh -i civic-extraction-key.pem ec2-user@13.217.205.13
sudo docker ps
sudo docker logs civic-extraction
```

**Restart container:**
```bash
sudo docker restart civic-extraction
```

**Test API locally on EC2:**
```bash
curl http://localhost/api/papers
```

---

## Features

- **Landing Page**: System overview with architecture diagrams
- **Paper Explorer**: Browse 15 research papers
- **PDF Viewer**: Built-in viewer with Range request support
- **Evidence Extraction**: View extracted clinical evidence
- **Knowledge Graph**: Interactive visualization
- **Checkpoints**: Resume capability for all extraction phases

---

## Tech Stack

- **Frontend**: React + Vite + PDF.js
- **Backend**: Node.js + Express
- **Web Server**: Nginx
- **Container**: Docker
- **Deployment**: AWS EC2 + ECR
- **Architecture**: ARM64 (Apple Silicon compatible)

---

## Notes

- **Firewall**: Corporate networks may block raw IPs. Access from personal network or use VPN.
- **Cost**: Free tier eligible (t4g.micro). ~$5-7/month after 12 months.
- **Data**: All PDFs and outputs included in Docker image.
- **Logs**: Available in container at `/app/logs/api.log`

---

## Quick Commands

```bash
# Local
docker compose up -d                                    # Start
docker compose logs -f                                   # View logs
docker compose down                                      # Stop

# AWS
ssh -i civic-extraction-key.pem ec2-user@13.217.205.13  # Connect
sudo docker logs civic-extraction                        # View logs
sudo docker restart civic-extraction                     # Restart
```

---

**Live Application:** http://13.217.205.13
