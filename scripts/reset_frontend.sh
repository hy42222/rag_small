#!/usr/bin/env bash
set -euo pipefail

API_URL_DEFAULT="http://localhost:8000"
TARGET_PORT=8500
LEGACY_PORTS=(8502 8503)
LOG_DIR="logs"

echo "[reset] Releasing ports and restarting Streamlit on ${TARGET_PORT} (API_URL=${API_URL:-$API_URL_DEFAULT})"

release_port() {
  local port="$1"
  echo "[reset] Releasing port ${port}..."
  # Try fuser first
  if command -v fuser >/dev/null 2>&1; then
    fuser -k "${port}"/tcp >/dev/null 2>&1 || true
  fi
  # Then try lsof
  if command -v lsof >/dev/null 2>&1; then
    pids=$(lsof -t -i :"${port}" -sTCP:LISTEN || true)
    if [ -n "${pids}" ]; then
      kill -TERM ${pids} >/dev/null 2>&1 || true
      sleep 1
      kill -KILL ${pids} >/dev/null 2>&1 || true
    fi
  fi
  # Finally ss to find pids
  if command -v ss >/dev/null 2>&1; then
    pids=$(ss -ltnp 2>/dev/null | awk -v p=":${port}" '$4 ~ p && $0 ~ /users:/ {print $0}' | sed -E 's/.*pid=([0-9]+).*/\\1/' | tr '\n' ' ')
    if [ -n "${pids}" ]; then
      kill -TERM ${pids} >/dev/null 2>&1 || true
      sleep 1
      kill -KILL ${pids} >/dev/null 2>&1 || true
    fi
  fi
}

release_port "${TARGET_PORT}"
for p in "${LEGACY_PORTS[@]}"; do
  release_port "${p}"
done

mkdir -p "${LOG_DIR}"
export API_URL="${API_URL:-$API_URL_DEFAULT}"

echo "[reset] Starting Streamlit on :${TARGET_PORT} (API_URL=${API_URL})..."
nohup python3 -m streamlit run frontend/app.py --server.port "${TARGET_PORT}" > "${LOG_DIR}/streamlit_${TARGET_PORT}.log" 2>&1 &
spid=$!
disown || true
echo "[reset] Streamlit started with PID ${spid}"

# Wait until port is open
for i in $(seq 1 30); do
  if curl -s -o /dev/null -w "%{http_code}" "http://localhost:${TARGET_PORT}" >/dev/null 2>&1; then
    echo "[reset] Streamlit is up on http://localhost:${TARGET_PORT}"
    exit 0
  fi
  sleep 0.5
done

echo "[reset] Warning: Streamlit did not become ready on port ${TARGET_PORT} in time" >&2
exit 1

