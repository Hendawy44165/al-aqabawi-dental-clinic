#!/usr/bin/env bash
# ==============================================================================
# spin_up.sh - Local Orchestrator for Dr. Al-Aqabawi Dental Clinic Chatbot
# Launches FastAPI backend (SQLite) and React frontend (Vite) using 'uv' & 'npm'.
# ==============================================================================

set -e

# Ensure common local bin directories are in PATH
export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

echo "=== 🦷 Dr. Al-Aqabawi Dental Clinic Bot Startup Orchestrator ==="

# ------------------------------------------------------------------------------
# 1. Prerequisite Checks
# ------------------------------------------------------------------------------
echo "🔍 Checking prerequisites..."

if ! command -v node &>/dev/null; then
  echo "❌ Error: Node.js is not installed."
  exit 1
fi

if ! command -v npm &>/dev/null; then
  echo "❌ Error: npm is not installed."
  exit 1
fi

if ! command -v uv &>/dev/null; then
  echo "❌ Error: 'uv' package manager is not installed."
  echo "   Install via: curl -LsSf https://astral.sh/uv/install.sh | sh"
  exit 1
fi

echo "✅ Prerequisites OK."

# ------------------------------------------------------------------------------
# 2. Dependency Check & Startup
# ------------------------------------------------------------------------------
echo "📦 Checking dependencies..."

if [ ! -d "$ROOT_DIR/frontend/node_modules" ]; then
  echo "Installing frontend dependencies..."
  cd "$ROOT_DIR/frontend" && npm install --no-audit --no-fund
fi

# Cleanup function on Ctrl+C
cleanup() {
  echo ""
  echo "🧹 Terminating services..."
  if [ -n "$BACKEND_PID" ]; then
    kill "$BACKEND_PID" 2>/dev/null || true
  fi
  if [ -n "$FRONTEND_PID" ]; then
    kill "$FRONTEND_PID" 2>/dev/null || true
  fi
  echo "✅ Shutdown complete. Exiting."
  exit 0
}

trap cleanup INT TERM

echo "🔥 Starting FastAPI Backend (uv uvicorn on port 8000)..."
cd "$ROOT_DIR/backend"
uv run uvicorn app:app --host 0.0.0.0 --port 8000 > /dev/null 2>&1 &
BACKEND_PID=$!

echo "🔥 Starting React Frontend Dashboard (Vite on port 5173)..."
cd "$ROOT_DIR/frontend"
npx vite --host 0.0.0.0 --port 5173 > /dev/null 2>&1 &
FRONTEND_PID=$!

echo ""
echo "=============================================================================="
echo "🎉 Al-Aqabawi Dental Clinic Chatbot is LIVE!"
echo "=============================================================================="
echo "📱 Frontend Simulator & Dashboard: http://localhost:5173"
echo "🔌 Backend API Docs (Swagger):      http://localhost:8000/docs"
echo "=============================================================================="
echo "🛑 Press Ctrl+C to stop all services."
echo "=============================================================================="

while true; do
  sleep 1
done
