#!/bin/bash
# Start FastAPI server for AI Pipeline

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}=====================================${NC}"
echo -e "${GREEN}  Musinsa AI Pipeline - API Server  ${NC}"
echo -e "${GREEN}=====================================${NC}"

# Activate virtual environment if exists
if [ -d "venv" ]; then
    echo -e "\n${YELLOW}Activating virtual environment...${NC}"
    source venv/bin/activate
fi

# Check Python version
echo -e "\n${YELLOW}Checking Python version...${NC}"
python3 --version

# Check CUDA
echo -e "\n${YELLOW}Checking CUDA availability...${NC}"
python3 - <<'PY'
try:
    import torch
    print(f'CUDA Available: {torch.cuda.is_available()}')
    print(f'CUDA Devices: {torch.cuda.device_count()}')
except Exception as e:
    print(f'CUDA check skipped: {e}')
PY

# Check Redis
echo -e "\n${YELLOW}Checking Redis connection...${NC}"
if redis-cli ping > /dev/null 2>&1; then
    echo -e "${GREEN}Redis is running${NC}"
else
    echo -e "${RED}Redis is not running. Please start Redis first:${NC}"
    echo -e "${YELLOW}  redis-server &${NC}"
    exit 1
fi

# Check if .env exists
if [ ! -f ".env" ]; then
    echo -e "\n${YELLOW}Creating .env from template...${NC}"
    cp .env.example .env
    echo -e "${RED}Please edit .env file and configure your settings${NC}"
    echo -e "${YELLOW}Then run this script again.${NC}"
    exit 1
fi

# Create directories
echo -e "\n${YELLOW}Creating necessary directories...${NC}"
python3 -c "from config import settings; settings.create_directories()"

# Start API server
echo -e "\n${GREEN}Starting FastAPI server...${NC}"
echo -e "${YELLOW}API will be available at: http://localhost:8001${NC}"
echo -e "${YELLOW}API documentation: http://localhost:8001/docs${NC}"
echo -e "\n"

cd api
python3 main.py
