#!/bin/sh
# Copyright (c) 2026 Zeta3. Parte di Atlante, copia modificata di Plane.
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.
#
# Writes the secrets of the test server next to this file: .env (database, queues, file storage, proxy),
# api.env (Atlante) and live.env (real-time editing). Random values, written only here, readable only by
# their owner, never printed and never in git. Run once on the server:
#
#   sh atlante/server/crea-segreti.sh collaudo.zeta3.it
#
# If the files are already there it changes nothing: the database keeps its password.

set -eu
cd "$(dirname "$0")"

DOMINIO=${1:?"Indica il dominio, per esempio collaudo.zeta3.it"}

if [ -e .env ] || [ -e api.env ] || [ -e live.env ]; then
	echo "I segreti esistono già: non li riscrivo."
	exit 0
fi

umask 077
casuale() { openssl rand -hex "$1"; }
PG=$(casuale 24)
MQ=$(casuale 24)
S3_UTENTE=$(casuale 10)
S3_CHIAVE=$(casuale 24)
DJANGO=$(casuale 32)
LIVE=$(casuale 24)

cat > .env <<EOF
POSTGRES_USER=atlante
POSTGRES_PASSWORD=$PG
POSTGRES_DB=atlante
RABBITMQ_DEFAULT_USER=atlante
RABBITMQ_DEFAULT_PASS=$MQ
RABBITMQ_DEFAULT_VHOST=atlante
MINIO_ROOT_USER=$S3_UTENTE
MINIO_ROOT_PASSWORD=$S3_CHIAVE
SITE_ADDRESS=$DOMINIO
FILE_SIZE_LIMIT=5242880
BUCKET_NAME=uploads
EOF

cat > api.env <<EOF
DEBUG=0
SECRET_KEY=$DJANGO
ALLOWED_HOSTS=$DOMINIO,localhost,api
CORS_ALLOWED_ORIGINS=https://$DOMINIO,http://localhost:8080
WEB_URL=https://$DOMINIO
APP_BASE_URL=https://$DOMINIO
APP_BASE_PATH=
ADMIN_BASE_PATH=/god-mode
SPACE_BASE_PATH=/spaces
LIVE_BASE_URL=https://$DOMINIO
LIVE_BASE_PATH=/live
LIVE_SERVER_SECRET_KEY=$LIVE
POSTGRES_USER=atlante
POSTGRES_PASSWORD=$PG
POSTGRES_HOST=plane-db
POSTGRES_DB=atlante
POSTGRES_PORT=5432
DATABASE_URL=postgresql://atlante:$PG@plane-db:5432/atlante
REDIS_HOST=plane-redis
REDIS_PORT=6379
REDIS_URL=redis://plane-redis:6379/
RABBITMQ_HOST=plane-mq
RABBITMQ_PORT=5672
RABBITMQ_USER=atlante
RABBITMQ_PASSWORD=$MQ
RABBITMQ_VHOST=atlante
AWS_REGION=
AWS_ACCESS_KEY_ID=$S3_UTENTE
AWS_SECRET_ACCESS_KEY=$S3_CHIAVE
AWS_S3_ENDPOINT_URL=http://plane-minio:9000
AWS_S3_BUCKET_NAME=uploads
USE_MINIO=1
MINIO_ENDPOINT_SSL=1
FILE_SIZE_LIMIT=5242880
GUNICORN_WORKERS=2
API_KEY_RATE_LIMIT=60/minute
HARD_DELETE_AFTER_DAYS=60
ENABLE_SIGNUP=0
ENABLE_EMAIL_PASSWORD=1
ENABLE_MAGIC_LINK_LOGIN=0
ATLANTE_AMBIENTE=prova
EOF

cat > live.env <<EOF
PORT=3000
API_BASE_URL=http://api:8000
WEB_BASE_URL=https://$DOMINIO
LIVE_BASE_URL=https://$DOMINIO
LIVE_BASE_PATH=/live
LIVE_SERVER_SECRET_KEY=$LIVE
REDIS_URL=redis://plane-redis:6379/
EOF

echo "Segreti scritti in $(pwd): .env, api.env, live.env (non mostrati)."
