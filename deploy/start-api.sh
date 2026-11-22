#!/bin/sh
# Starts the local inbox, then the API. If the API process dies (a kill, a crash) it is started again in the
# same container, so the database file survives and the restart resumes from what was recorded.
mailpit --smtp 127.0.0.1:1025 --listen 127.0.0.1:8025 &
cd /app/server
while true; do
  python -m uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
  echo "api process exited with code $?; restarting in 1 second"
  sleep 1
done
