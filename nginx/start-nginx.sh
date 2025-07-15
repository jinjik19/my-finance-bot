#!/bin/sh

set -e

TEMPLATE_DIR="/etc/nginx/templates"
CONF_DIR="/etc/nginx/conf.d"
HTTP_TEMPLATE="$TEMPLATE_DIR/metabase-http.template"
HTTPS_TEMPLATE="$TEMPLATE_DIR/metabase-https.template"
CONF_FILE="$CONF_DIR/metabase.conf"

echo "Проверяем наличие сертификатов для $METABASE_DOMAIN..."
if [ -f "/etc/nginx/ssl/$METABASE_DOMAIN/fullchain.pem" ] && [ -f "/etc/nginx/ssl/$METABASE_DOMAIN/privkey.pem" ]; then
    echo "Сертификаты найдены, запускаем nginx с SSL..."
    envsubst '${METABASE_DOMAIN}' < "$HTTPS_TEMPLATE" > "$CONF_FILE"
    exec nginx -g 'daemon off;'
else
    echo "Сертификаты не найдены, запускаем nginx без SSL..."
    envsubst '${METABASE_DOMAIN}' < "$HTTP_TEMPLATE" > "$CONF_FILE"
    nginx -g 'daemon off;' &
    NGINX_PID=$!

    echo "Ждём 5 секунд для запуска nginx..."
    sleep 5

    echo "Запускаем certbot для получения сертификатов..."
    certbot certonly --webroot -w /var/www/certbot --email "$CERTBOT_EMAIL" -d "$METABASE_DOMAIN" --agree-tos --non-interactive --force-renewal

    echo "Останавливаем nginx..."
    kill -TERM $NGINX_PID
    wait $NGINX_PID

    echo "Подставляем конфиг с SSL..."
    envsubst '${METABASE_DOMAIN}' < "$HTTPS_TEMPLATE" > "$CONF_FILE"

    echo "Запускаем nginx с SSL..."
    exec nginx -g 'daemon off;'
fi
