#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="/home/MadCamp/MadCamp_3week"
LOG_DIR="$ROOT_DIR/logs/dev"
mkdir -p "$LOG_DIR"

start_process() {
  local name="$1"
  local cmd="$2"
  local pid_file="$LOG_DIR/${name}.pid"
  local log_file="$LOG_DIR/${name}.log"

  if [[ -f "$pid_file" ]]; then
    local pid
    pid=$(cat "$pid_file") || true
    if [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null; then
      echo "[$name] already running (pid=$pid)"
      return
    fi
  fi

  echo "[$name] starting..."
  bash -lc "$cmd" > "$log_file" 2>&1 &
  echo $! > "$pid_file"
  echo "[$name] started (pid=$(cat "$pid_file"))"
}

# Ensure Redis is running if available
REDIS_AVAILABLE=true
if ! command -v redis-cli >/dev/null 2>&1; then
  REDIS_AVAILABLE=false
  echo "[redis] redis-cli not found. Running without Redis/Celery."
else
  if ! redis-cli ping >/dev/null 2>&1; then
    if command -v redis-server >/dev/null 2>&1; then
      echo "[redis] starting..."
      redis-server --daemonize yes
    else
      REDIS_AVAILABLE=false
      echo "[redis] redis-server not found. Running without Redis/Celery."
    fi
  fi
fi

# Backend API
start_process "backend" "cd $ROOT_DIR/backend && if [ -d venv ]; then source venv/bin/activate; fi; python3 -m uvicorn main:app --reload --host 0.0.0.0 --port 8000"

# AI Pipeline API (start directly if Redis unavailable)
if [[ "$REDIS_AVAILABLE" == "true" ]]; then
  start_process "ai_api" "cd $ROOT_DIR/ai-pipeline && ./start_api.sh"
  start_process "ai_celery" "cd $ROOT_DIR/ai-pipeline && ./start_celery.sh"
else
  start_process "ai_api" "cd $ROOT_DIR/ai-pipeline && if [ -d venv ]; then source venv/bin/activate; fi; python3 api/main.py"
fi

# Frontend
if [[ ! -d "$ROOT_DIR/frontend/node_modules" ]]; then
  echo "[frontend] installing dependencies..."
  (cd "$ROOT_DIR/frontend" && npm install)
fi
start_process "frontend" "cd $ROOT_DIR/frontend && npm run dev -- --port 3000"

echo "All services started. Logs: $LOG_DIR"
