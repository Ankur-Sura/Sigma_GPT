#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Always run from the project root so the advanced_rag package is importable.
cd "$PROJECT_ROOT"

# Ensure Python can import the advanced_rag package.
export PYTHONPATH="$PROJECT_ROOT:${PYTHONPATH:-}"

# Prevent macOS Objective-C fork safety crash when RQ forks workers.
export OBJC_DISABLE_INITIALIZE_FORK_SAFETY=YES

# Load local environment variables (OPENAI_API_KEY, etc.).
if [ -f "$SCRIPT_DIR/.env" ]; then
  set -a
  # shellcheck disable=SC1090
  source "$SCRIPT_DIR/.env"
  set +a
fi

# Start the RQ worker (non-forking) with scheduler enabled.
rq worker --with-scheduler --worker-class rq.worker.SimpleWorker advanced_rag.queue.connection
