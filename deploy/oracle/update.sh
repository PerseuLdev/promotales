#!/bin/bash
# Script de atualizacao do PromoTales Bot

set -e

INSTALL_DIR="/opt/promotales"

echo "=== PromoTales Bot - Atualizacao ==="
echo ""

cd $INSTALL_DIR

# Para o bot
echo "[1/4] Parando o bot..."
sudo systemctl stop promotales || true

# Atualiza codigo
echo "[2/4] Atualizando codigo..."
git pull origin main

# Atualiza dependencias
echo "[3/4] Atualizando dependencias..."
source venv/bin/activate
pip install -r requirements.txt

# Reinicia o bot
echo "[4/4] Reiniciando o bot..."
sudo systemctl start promotales

echo ""
echo "=== Atualizacao concluida! ==="
sudo systemctl status promotales --no-pager
