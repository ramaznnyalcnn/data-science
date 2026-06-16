#!/usr/bin/env bash
# Starts four local Streamlit replicas for development testing.
# In production, prefer the systemd template: travel-rec@8501..8504.
set -euo pipefail

cd "$(dirname "$0")/.."
PYTHON="${PYTHON:-python3}"
PORTS=(8501 8502 8503 8504)

mkdir -p logs
pids=()
trap 'echo "[stop] killing replicas..."; kill "${pids[@]}" 2>/dev/null || true; wait 2>/dev/null || true' INT TERM EXIT

for p in "${PORTS[@]}"; do
    echo "[start] streamlit replica :$p"
    "$PYTHON" -m streamlit run app/main.py         --server.address 127.0.0.1         --server.port "$p"         --server.headless true         > "logs/streamlit-$p.log" 2>&1 &
    pids+=("$!")
done

echo "[ready] 4 replicas: ${PORTS[*]} (logs/streamlit-<port>.log)"
echo "[hint] use nginx locally or the systemd template in production"
wait
