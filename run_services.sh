#!/bin/sh
set -eu

PROJECT_DIR="/opt/data/workspace/hermes-feegow-mcp"
export PYTHONPATH="$PROJECT_DIR/src"
cd "$PROJECT_DIR"

# Credencial do git fica no volume persistente - $HOME nao sobrevive a redeploy.
git config --global credential.helper "store --file=/opt/data/.git-credentials" 2>/dev/null || true

# Corrige permissoes da pasta whatsapp-bridge para o usuario hermes poder rodar npm install
chown -R hermes:hermes /opt/hermes/scripts/whatsapp-bridge 2>/dev/null || true
chmod -R u+w /opt/hermes/scripts/whatsapp-bridge 2>/dev/null || true

WEBHOOK_PID=""
GATEWAY_PID=""

cleanup() {
    [ -z "$WEBHOOK_PID" ] || kill "$WEBHOOK_PID" 2>/dev/null || true
    [ -z "$GATEWAY_PID" ] || kill "$GATEWAY_PID" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

uv run uvicorn ana_feegow.webhooks.app:app \
    --host 0.0.0.0 \
    --port 9120 \
    --env-file .env &
WEBHOOK_PID=$!

if [ "${HERMES_START_GATEWAY:-0}" = "1" ]; then
    (
        set +e
        trap 'kill -TERM "$child" 2>/dev/null; exit 0' TERM INT
        while true; do
            hermes gateway run &
            child=$!
            wait "$child"
            code=$?
            echo "[run_services] gateway exited (code=$code), restarting in 3s..." >&2
            sleep 3
        done
    ) &
    GATEWAY_PID=$!
fi

exec hermes dashboard --host 0.0.0.0 --port 9119 --skip-build
