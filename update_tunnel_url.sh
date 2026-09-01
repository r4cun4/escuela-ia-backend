#!/bin/sh
# update_tunnel_url.sh
# Se ejecuta cada vez que cloudflared arranca y detecta la URL del túnel.
# Actualiza el webhook de Telegram y la variable WEBHOOK_URL de n8n automáticamente.

set -e

CLOUDFLARED_LOGS="/tmp/cloudflared.log"
N8N_URL="http://n8n:5678"
TELEGRAM_BOT_TOKEN="${TELEGRAM_BOT_TOKEN}"
TELEGRAM_WEBHOOK_PATH="/webhook/telegram"

echo "[tunnel-watcher] Esperando que cloudflared exponga la URL..."

# Espera hasta 30 segundos para que aparezca la URL en los logs
for i in $(seq 1 30); do
    TUNNEL_URL=$(cloudflared tunnel --url "$N8N_URL" 2>&1 | grep -oP 'https://[a-z0-9\-]+\.trycloudflare\.com' | head -1)
    if [ -n "$TUNNEL_URL" ]; then
        break
    fi
    sleep 1
done

if [ -z "$TUNNEL_URL" ]; then
    echo "[tunnel-watcher] ERROR: No se pudo detectar la URL del túnel."
    exit 1
fi

echo "[tunnel-watcher] URL detectada: $TUNNEL_URL"

# Actualizar webhook de Telegram
WEBHOOK_URL="${TUNNEL_URL}${TELEGRAM_WEBHOOK_PATH}"
echo "[tunnel-watcher] Actualizando webhook de Telegram a: $WEBHOOK_URL"

curl -s -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/setWebhook" \
    -d "url=${WEBHOOK_URL}" | cat

echo ""
echo "[tunnel-watcher] Listo!"
