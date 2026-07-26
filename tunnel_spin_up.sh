#!/usr/bin/env bash
# ==============================================================================
# tunnel_spin_up.sh - Instant Mobile Access Launcher for Al-Aqabawi Dental Clinic
# Launches FastAPI backend (port 8000) & React frontend (port 5173) and creates
# a public HTTPS tunnel via localtunnel for instant mobile testing.
# ==============================================================================

set -e

# Ensure common local bin directories are in PATH
export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

echo "=============================================================================="
echo "🦷 Al-Aqabawi Dental Clinic - Instant Mobile Access Launcher"
echo "=============================================================================="

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

if ! command -v npx &>/dev/null; then
  echo "❌ Error: npx is not installed."
  exit 1
fi

if ! command -v uv &>/dev/null; then
  echo "❌ Error: 'uv' package manager is not installed."
  echo "   Install via: curl -LsSf https://astral.sh/uv/install.sh | sh"
  exit 1
fi

echo "✅ Prerequisites verified."

# ------------------------------------------------------------------------------
# 2. Dependency Verification
# ------------------------------------------------------------------------------
if [ ! -d "$ROOT_DIR/frontend/node_modules" ]; then
  echo "📦 Installing frontend dependencies..."
  cd "$ROOT_DIR/frontend" && npm install --no-audit --no-fund
  cd "$ROOT_DIR"
fi

# ------------------------------------------------------------------------------
# 3. Cleanup Trap
# ------------------------------------------------------------------------------
cleanup() {
  echo ""
  echo "🧹 Shutting down active services..."
  if [ -n "$BACKEND_PID" ]; then
    kill "$BACKEND_PID" 2>/dev/null || true
  fi
  if [ -n "$FRONTEND_PID" ]; then
    kill "$FRONTEND_PID" 2>/dev/null || true
  fi
  if [ -n "$TUNNEL_PID" ]; then
    kill "$TUNNEL_PID" 2>/dev/null || true
  fi
  echo "✅ Shutdown complete. All processes terminated."
  exit 0
}

trap cleanup INT TERM

# ------------------------------------------------------------------------------
# 4. Launch FastAPI Backend
# ------------------------------------------------------------------------------
echo "🔥 Starting FastAPI Backend (uv on port 8000)..."
cd "$ROOT_DIR/backend"
uv run uvicorn app:app --host 0.0.0.0 --port 8000 > /dev/null 2>&1 &
BACKEND_PID=$!
cd "$ROOT_DIR"

# ------------------------------------------------------------------------------
# 5. Launch React Frontend
# ------------------------------------------------------------------------------
echo "🔥 Starting React Frontend (npm run dev on port 5173)..."
cd "$ROOT_DIR/frontend"
npm run dev -- --host 0.0.0.0 --port 5173 > /dev/null 2>&1 &
FRONTEND_PID=$!
cd "$ROOT_DIR"

# Wait for local servers to start
echo "⏳ Waiting for local servers to initialize..."
sleep 3

# ------------------------------------------------------------------------------
# 6. Expose Public Tunnel via localtunnel
# ------------------------------------------------------------------------------
echo "🌐 Spawning Public HTTPS Tunnel on port 5173..."
echo "=============================================================================="

npx localtunnel --port 5173 &
TUNNEL_PID=$!

echo "=============================================================================="
echo "🎉 Al-Aqabawi Dental Clinic is LIVE locally and accessible remotely!"
echo "=============================================================================="
echo "💻 Local Frontend: http://localhost:5173"
echo "🔌 Local API Docs: http://localhost:8000/docs"
echo "📱 Public Mobile HTTPS URL: Check the localtunnel output above ⬆️"
echo "=============================================================================="
echo "🛑 Press Ctrl+C to stop all background processes."
echo "=============================================================================="

while true; do
  sleep 1
done
