#!/bin/bash
# Script de instalacao do PromoTales Bot
# Execute apos o setup.sh

set -e

INSTALL_DIR="/opt/promotales"
REPO_URL="https://github.com/SEU_USUARIO/PromoTales-DrissionPage.git"

echo "=== PromoTales Bot - Instalacao ==="
echo ""

# Verifica se esta no diretorio correto
if [ ! -d "$INSTALL_DIR" ]; then
    echo "Erro: Diretorio $INSTALL_DIR nao existe"
    echo "Execute setup.sh primeiro"
    exit 1
fi

cd $INSTALL_DIR

# Verifica se .env existe
if [ ! -f ".env" ]; then
    echo "Erro: Arquivo .env nao encontrado"
    echo "Crie o arquivo .env com:"
    echo "  BOT_TOKEN=seu_token_aqui"
    exit 1
fi

# Cria virtual environment
echo "[1/4] Criando ambiente virtual..."
python3.11 -m venv venv
source venv/bin/activate

# Instala dependencias Python
echo "[2/4] Instalando dependencias Python..."
pip install --upgrade pip
pip install -r requirements.txt

# Cria diretorios de dados
echo "[3/4] Criando diretorios..."
mkdir -p data
mkdir -p logs

# Instala e habilita o service
echo "[4/4] Configurando systemd..."
sudo cp deploy/oracle/promotales.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable promotales

echo ""
echo "=== Instalacao concluida! ==="
echo ""
echo "Comandos uteis:"
echo "  sudo systemctl start promotales   - Iniciar bot"
echo "  sudo systemctl stop promotales    - Parar bot"
echo "  sudo systemctl restart promotales - Reiniciar bot"
echo "  sudo systemctl status promotales  - Ver status"
echo "  sudo journalctl -u promotales -f  - Ver logs em tempo real"
echo ""
echo "Logs:"
echo "  /opt/promotales/logs/promotales.log"
echo "  /opt/promotales/logs/promotales.error.log"
echo ""
echo "Cache SQLite:"
echo "  /opt/promotales/data/cache.db"
