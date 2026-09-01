#!/bin/sh
# Espera a que cloudflared exponga la URL en sus logs y actualiza:
# 1. El webhook de Telegram
# 2. La variable de entorno WEBHOOK_URL de n8n (vía restart con nuevo valor)

echo "[tunnel-watcher] Esperando URL de cloudflared..."

# Loop hasta conseguir la URL de los logs del contenedor cloudflared
TUNNEL_URL=""
for i in $(seq 1 60); do
    TUNNEL_URL=$(cat /cloudflared_logs/output.log 2>/dev/null | grep -oE 'https://[a-z0-9-]+\.trycloudflare\.com' | head -1)
    if [ -n "$TUNNEL_URL" ]; then
        break
    fi
    sleep 2
done

if [ -z "$TUNNEL_URL" ]; then
    echo "[tunnel-watcher] ERROR: No se detectó URL en 120 segundos."
    exit 1
fi

echo "[tunnel-watcher] URL del túnel: $TUNNEL_URL"

# Actualizar webhook de Telegram
if [ -n "$TELEGRAM_BOT_TOKEN" ]; then
    WEBHOOK_FULL="${TUNNEL_URL}/webhook/telegram"
    echo "[tunnel-watcher] Actualizando Telegram webhook -> $WEBHOOK_FULL"
    RESULT=$(curl -s "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/setWebhook?url=${WEBHOOK_FULL}")
    echo "[tunnel-watcher] Telegram: $RESULT"
fi

echo "[tunnel-watcher] Guardando URL en /data/tunnel_url.txt"
echo "$TUNNEL_URL" > /data/tunnel_url.txt

echo "[tunnel-watcher] Completado."
