#!/bin/bash
# Script de setup para Oracle Cloud Ubuntu 22.04+
# Instala todas as dependencias necessarias para o PromoTales Bot

set -e

echo "=== PromoTales Bot - Setup Oracle Cloud ==="
echo ""

# Atualiza sistema
echo "[1/6] Atualizando sistema..."
sudo apt update && sudo apt upgrade -y

# Instala dependencias do sistema
echo "[2/6] Instalando dependencias do sistema..."
sudo apt install -y \
    python3.11 \
    python3.11-venv \
    python3-pip \
    git \
    wget \
    unzip \
    xvfb \
    fonts-liberation \
    libasound2 \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libatspi2.0-0 \
    libcups2 \
    libdbus-1-3 \
    libdrm2 \
    libgbm1 \
    libgtk-3-0 \
    libnspr4 \
    libnss3 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxkbcommon0 \
    libxrandr2

# Instala Chromium (mais leve que Chrome)
echo "[3/6] Instalando Chromium..."
sudo apt install -y chromium-browser

# Verifica instalacao do Chromium
CHROME_PATH=$(which chromium-browser || which chromium)
echo "Chromium instalado em: $CHROME_PATH"

# Configura swap (importante para 1GB RAM)
echo "[4/6] Configurando swap..."
if [ ! -f /swapfile ]; then
    sudo fallocate -l 1G /swapfile
    sudo chmod 600 /swapfile
    sudo mkswap /swapfile
    sudo swapon /swapfile
    echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
    echo "Swap de 1GB configurado"
else
    echo "Swap ja existe"
fi

# Mostra memoria
echo ""
echo "=== Memoria disponivel ==="
free -h

# Cria diretorio para o bot
echo "[5/6] Criando diretorios..."
sudo mkdir -p /opt/promotales
sudo mkdir -p /opt/promotales/data
sudo mkdir -p /opt/promotales/logs
sudo chown -R $USER:$USER /opt/promotales

# Cria usuario do sistema (opcional, para producao)
# sudo useradd -r -s /bin/false promotales || true

echo "[6/6] Setup concluido!"
echo ""
echo "=== Proximos passos ==="
echo "1. Clone o repositorio em /opt/promotales"
echo "2. Crie o arquivo .env com BOT_TOKEN"
echo "3. Execute: ./install.sh"
echo "4. Execute: sudo systemctl start promotales"
