#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="/home/MadCamp/MadCamp_3week"
LOG_DIR="$ROOT_DIR/logs/dev"

stop_process() {
  local name="$1"
  local pid_file="$LOG_DIR/${name}.pid"

  if [[ ! -f "$pid_file" ]]; then
    echo "[$name] no pid file"
    return
  fi

  local pid
  pid=$(cat "$pid_file") || true
  if [[ -z "$pid" ]]; then
    echo "[$name] pid file empty"
    return
  fi

  if kill -0 "$pid" 2>/dev/null; then
    echo "[$name] stopping (pid=$pid)"
    kill "$pid" || true
  else
    echo "[$name] not running"
  fi

  rm -f "$pid_file"
}

stop_process "frontend"
stop_process "ai_celery"
stop_process "ai_api"
stop_process "backend"

echo "Stopped services."
