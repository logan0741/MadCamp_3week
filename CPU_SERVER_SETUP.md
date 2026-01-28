# 🖥️ CPU Server Setup Guide

> **Server Information**
> - **IP Address**: `172.10.5.40`
> - **Password**: `1234`
> - **OS**: Ubuntu (Assumed Linux environment)
> - **Purpose**: Host Backend API & Crawler

---

## 1. Initial Connection
SSH into the server:
```bash
ssh root@172.10.5.40
# Enter password: 1234
```

## 2. System Preparation
Update package lists and install necessary system tools.
```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3.11 python3-pip python3-venv unzip git curl
```
*(Note: Python 3.10+ is recommended)*

## 3. Project Deployment
Create a directory for the backend and navigate into it.
```bash
mkdir -p ~/musinsa-backend
cd ~/musinsa-backend
```
*At this step, upload your project files (via SCP or Git).*

## 4. Python Environment Setup
Create a virtual environment to manage dependencies cleanly.
```bash
# Create virtual environment named 'venv'
python3 -m venv venv

# Activate the environment
source venv/bin/activate
```

## 5. Install Dependencies
Install all required Python libraries for the backend and crawler.
```bash
# Core Backend & Scraper
pip install fastapi uvicorn[standard] sqlalchemy httpx apscheduler

# Data Validation & Settings
pip install pydantic pydantic-settings

# Database Adapter
pip install psycopg2-binary
```

## 6. Playwright Setup (Critical for Crawler)
Playwright requires browser binaries and system dependencies to function correctly.
```bash
# Install Playwright Python package
pip install playwright

# Download Chromium browser binary
playwright install chromium

# Install system-level dependencies for Chromium (requires sudo)
sudo playwright install-deps
```

## 7. Running the Server
### Development Mode (See logs directly)
```bash
python3 -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### Production Mode (Background Service)
Run the server in the background so it stays alive after SSH disconnects.
```bash
nohup python3 -m uvicorn main:app --host 0.0.0.0 --port 8000 > server.log 2>&1 &
```

---

## ✅ Verification
Test if the server and crawler are working:

1.  **Check Health Endpoint**:
    ```bash
    curl http://localhost:8000/health
    # Response: {"status": "healthy"}
    ```

2.  **Test Scraper** (Optional, if test script exists):
    ```bash
    python3 test_scraper.py
    ```

---
** Troubleshooting **:
- If `playwright` errors occur, ensure `sudo playwright install-deps` ran successfully.
- If `uvicorn` is not found, ensure the virtual environment is activated (`source venv/bin/activate`).
