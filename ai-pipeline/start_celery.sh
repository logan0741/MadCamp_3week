#!/bin/bash
# Start Celery worker for AI Pipeline

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}=====================================${NC}"
echo -e "${GREEN}  Musinsa AI Pipeline - Celery Worker${NC}"
echo -e "${GREEN}=====================================${NC}"

# Check Redis
echo -e "\n${YELLOW}Checking Redis connection...${NC}"
if ! redis-cli ping > /dev/null 2>&1; then
    echo -e "${RED}Redis is not running. Please start Redis first:${NC}"
    echo -e "${YELLOW}  redis-server &${NC}"
    exit 1
fi

# Activate venv
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Worker configuration
CONCURRENCY=${CELERY_CONCURRENCY:-2}
LOGLEVEL=${CELERY_LOGLEVEL:-info}
QUEUES=${CELERY_QUEUES:-vton,avatar,garment}

echo -e "\n${YELLOW}Starting Celery worker with:${NC}"
echo -e "  Concurrency: $CONCURRENCY"
echo -e "  Log Level: $LOGLEVEL"
echo -e "  Queues: $QUEUES"
echo -e "\n"

# Start worker
celery -A workers.celery_app worker \
    --loglevel=$LOGLEVEL \
    --concurrency=$CONCURRENCY \
    --max-tasks-per-child=10 \
    --queues=$QUEUES \
    --hostname=worker1@%h
