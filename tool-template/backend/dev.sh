#!/usr/bin/env bash
# Frees port 8000 if an old uvicorn is stuck, then runs the app.
set -e
cd "$(dirname "$0")"
pid=$(lsof -nP -iTCP:8000 -sTCP:LISTEN -t 2>/dev/null || true)
if [ -n "$pid" ]; then
  echo "Killing old listener on :8000 (PID $pid)"
  kill "$pid" 2>/dev/null || true
  sleep 0.5
fi
exec python3 -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
