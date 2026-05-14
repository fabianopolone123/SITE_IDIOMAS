#!/usr/bin/env bash
set -euo pipefail

APP_DIR="${APP_DIR:-/var/www/site_idiomas}"
BRANCH="${BRANCH:-main}"
SERVICE="${SERVICE:-site_idiomas}"

cd "$APP_DIR"

echo "==> Atualizando codigo"
git fetch origin "$BRANCH"
git pull --ff-only origin "$BRANCH"

echo "==> Ativando ambiente virtual"
source .venv/bin/activate

echo "==> Instalando dependencias"
pip install -r requirements.txt

echo "==> Aplicando migracoes"
python manage.py migrate --noinput

echo "==> Importando cards sem apagar progresso"
python manage.py import_alice_phrases

echo "==> Coletando arquivos estaticos"
python manage.py collectstatic --noinput

echo "==> Validando Django"
python manage.py check

echo "==> Reiniciando servico"
systemctl restart "$SERVICE"
systemctl status "$SERVICE" --no-pager

echo "==> Atualizacao concluida: https://fabianopolone.com.br"
