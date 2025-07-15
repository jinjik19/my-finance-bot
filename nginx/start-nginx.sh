#!/bin/sh

set -e

TEMPLATE_DIR="/etc/nginx/templates"
CONF_DIR="/etc/nginx/conf.d"
HTTP_TEMPLATE="$TEMPLATE_DIR/metabase-http.template"
HTTPS_TEMPLATE="$TEMPLATE_DIR/metabase-https.template"
CONF_FILE="$CONF_DIR/metabase.conf"
SSL_DIR="/etc/nginx/ssl/$METABASE_DOMAIN"

echo "Проверяем наличие сертификатов для $METABASE_DOMAIN..."

if [ -f "$SSL_DIR/fullchain.pem" ] && [ -f "$SSL_DIR/privkey.pem" ]; then
    echo "Сертификаты найдены. Используем HTTPS конфиг."
    envsubst '${METABASE_DOMAIN}' < "$HTTPS_TEMPLATE" > "$CONF_FILE"
else
    echo "Сертификаты не найдены. Используем HTTP конфиг."
    envsubst '${METABASE_DOMAIN}' < "$HTTP_TEMPLATE" > "$CONF_FILE"
fi

echo "Запускаем nginx..."
exec nginx -g 'daemon off;'
