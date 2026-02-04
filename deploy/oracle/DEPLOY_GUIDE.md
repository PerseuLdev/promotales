# Guia Completo: Deploy PromoTales no Oracle Cloud

## Parte 1: Criar Conta Oracle Cloud (Free Tier)

### 1.1 Cadastro
1. Acesse: https://www.oracle.com/cloud/free/
2. Clique em **"Start for free"**
3. Preencha seus dados (precisa de cartão de crédito, mas NÃO será cobrado)
4. Selecione a região **Brazil East (Sao Paulo)** - `sa-saopaulo-1`
5. Complete a verificação por email

### 1.2 Aguarde Ativação
- A conta pode levar até 24h para ativar
- Você receberá um email quando estiver pronta

---

## Parte 2: Criar Instância de Computação

### 2.1 Acessar Console
1. Acesse: https://cloud.oracle.com/
2. Faça login com suas credenciais
3. No menu lateral, vá em: **Compute** → **Instances**

### 2.2 Criar Instância
1. Clique em **"Create instance"**

2. **Name:** `promotales-bot`

3. **Placement:** Mantenha o padrão (AD-1)

4. **Image and shape:**
   - Clique em **"Edit"**
   - **Image:** Ubuntu 22.04 (ou 24.04)
   - **Shape:** Clique em "Change shape"
     - Selecione **"Ampere"** (ARM) - É FREE TIER!
     - Shape: `VM.Standard.A1.Flex`
     - OCPUs: `1`
     - Memory: `6 GB` (máximo free tier)

   > ⚠️ Se Ampere não estiver disponível, use:
   > - Shape: `VM.Standard.E2.1.Micro` (AMD)
   > - 1 OCPU, 1 GB RAM

5. **Networking:**
   - Mantenha o padrão (cria nova VCN)
   - **Public IPv4 address:** Marque "Assign a public IPv4 address"

6. **Add SSH keys:**
   - Selecione **"Generate a key pair for me"**
   - Clique em **"Save private key"**
   - Salve o arquivo `ssh-key-XXXX.key` em local seguro!

   > ⚠️ IMPORTANTE: Guarde essa chave! Sem ela você não consegue acessar a VM.

7. **Boot volume:**
   - Mantenha o padrão (47 GB)

8. Clique em **"Create"**

### 2.3 Aguardar Provisionamento
- O status mudará de "PROVISIONING" para "RUNNING"
- Anote o **Public IP Address** (ex: `152.70.xxx.xxx`)

---

## Parte 3: Configurar Firewall (Security List)

### 3.1 Liberar Portas
1. Na página da instância, clique no nome da **Subnet** (em "Primary VNIC")
2. Clique na **Security List** (geralmente `Default Security List...`)
3. Clique em **"Add Ingress Rules"**
4. Adicione a regra:
   - **Source CIDR:** `0.0.0.0/0`
   - **Destination Port Range:** `22`
   - **Description:** SSH
5. Clique em **"Add Ingress Rules"**

> Nota: Para o bot do Telegram, não precisamos abrir outras portas (ele faz polling).

---

## Parte 4: Conectar via SSH

### 4.1 Windows (PowerShell ou Git Bash)

```powershell
# Mova a chave para pasta segura
mkdir $HOME\.ssh -ErrorAction SilentlyContinue
mv Downloads\ssh-key-*.key $HOME\.ssh\oracle-key.pem

# Ajuste permissões (PowerShell como Admin)
icacls "$HOME\.ssh\oracle-key.pem" /inheritance:r /grant:r "$env:USERNAME:R"

# Conecte
ssh -i $HOME\.ssh\oracle-key.pem ubuntu@SEU_IP_PUBLICO
```

### 4.2 Linux/Mac

```bash
# Mova a chave
mv ~/Downloads/ssh-key-*.key ~/.ssh/oracle-key.pem
chmod 600 ~/.ssh/oracle-key.pem

# Conecte
ssh -i ~/.ssh/oracle-key.pem ubuntu@SEU_IP_PUBLICO
```

### 4.3 Primeira Conexão
- Digite `yes` quando perguntado sobre fingerprint
- Você deve ver: `ubuntu@promotales-bot:~$`

---

## Parte 5: Instalar Dependências

### 5.1 Atualizar Sistema

```bash
sudo apt update && sudo apt upgrade -y
```

### 5.2 Instalar Python e Dependências

```bash
# Python 3.11+
sudo apt install -y python3.11 python3.11-venv python3-pip git wget unzip

# Dependências do Chromium
sudo apt install -y \
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
```

### 5.3 Instalar Chromium

```bash
sudo apt install -y chromium-browser

# Verificar instalação
chromium-browser --version
```

### 5.4 Configurar Swap (IMPORTANTE para 1GB RAM)

```bash
# Criar swap de 2GB
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile

# Tornar permanente
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab

# Verificar
free -h
```

Saída esperada:
```
              total        used        free      shared  buff/cache   available
Mem:          981Mi       150Mi       500Mi       1.0Mi       330Mi       700Mi
Swap:         2.0Gi          0B       2.0Gi
```

---

## Parte 6: Instalar PromoTales Bot

### 6.1 Clonar Repositório

```bash
# Criar diretório
sudo mkdir -p /opt/promotales
sudo chown $USER:$USER /opt/promotales
cd /opt/promotales

# Clonar (substitua pela sua URL)
git clone https://github.com/SEU_USUARIO/PromoTales-DrissionPage.git .

# OU se for repositório privado, use token:
# git clone https://TOKEN@github.com/SEU_USUARIO/PromoTales-DrissionPage.git .
```

### 6.2 Criar Ambiente Virtual

```bash
cd /opt/promotales
python3.11 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### 6.3 Configurar Variáveis de Ambiente

```bash
# Criar arquivo .env
cat > /opt/promotales/.env << 'EOF'
BOT_TOKEN=SEU_TOKEN_AQUI
EOF

# Editar com seu token real
nano /opt/promotales/.env
```

> Para sair do nano: `Ctrl+X`, depois `Y`, depois `Enter`

### 6.4 Criar Diretórios

```bash
mkdir -p /opt/promotales/data
mkdir -p /opt/promotales/logs
```

### 6.5 Testar Manualmente

```bash
cd /opt/promotales
source venv/bin/activate

# Definir variáveis de ambiente para produção
export ORACLE_CLOUD=1
export ENVIRONMENT=production
export CACHE_TYPE=sqlite
export HEADLESS=true
export CHROME_BIN=/usr/bin/chromium-browser

# Rodar o bot
python -m src.main
```

Se funcionar, você verá:
```
Bot rodando no Oracle Cloud (modo producao)
Cache: sqlite | TTL=300s
Bot iniciado com sucesso. Aguardando mensagens...
```

Pressione `Ctrl+C` para parar.

---

## Parte 7: Configurar Systemd (Rodar como Serviço)

### 7.1 Criar Service File

```bash
sudo nano /etc/systemd/system/promotales.service
```

Cole o conteúdo:

```ini
[Unit]
Description=PromoTales Telegram Bot
After=network.target
StartLimitIntervalSec=0

[Service]
Type=simple
User=ubuntu
Group=ubuntu
WorkingDirectory=/opt/promotales
Environment="ORACLE_CLOUD=1"
Environment="ENVIRONMENT=production"
Environment="CACHE_TYPE=sqlite"
Environment="SQLITE_DB_PATH=/opt/promotales/data/cache.db"
Environment="CHROME_BIN=/usr/bin/chromium-browser"
Environment="HEADLESS=true"
EnvironmentFile=/opt/promotales/.env
ExecStart=/opt/promotales/venv/bin/python -m src.main
Restart=always
RestartSec=10

# Limites de recursos
MemoryMax=800M
MemoryHigh=700M

# Logs
StandardOutput=append:/opt/promotales/logs/promotales.log
StandardError=append:/opt/promotales/logs/promotales.error.log

[Install]
WantedBy=multi-user.target
```

Salve: `Ctrl+X`, `Y`, `Enter`

### 7.2 Habilitar e Iniciar

```bash
# Recarregar systemd
sudo systemctl daemon-reload

# Habilitar inicio automático
sudo systemctl enable promotales

# Iniciar o bot
sudo systemctl start promotales

# Verificar status
sudo systemctl status promotales
```

Saída esperada:
```
● promotales.service - PromoTales Telegram Bot
     Loaded: loaded (/etc/systemd/system/promotales.service; enabled)
     Active: active (running) since ...
```

---

## Parte 8: Comandos Úteis

### Ver Logs em Tempo Real

```bash
# Logs do systemd
sudo journalctl -u promotales -f

# Logs do arquivo
tail -f /opt/promotales/logs/promotales.log
```

### Gerenciar o Serviço

```bash
# Parar
sudo systemctl stop promotales

# Reiniciar
sudo systemctl restart promotales

# Status
sudo systemctl status promotales
```

### Atualizar o Bot

```bash
cd /opt/promotales
sudo systemctl stop promotales
git pull origin main
source venv/bin/activate
pip install -r requirements.txt
sudo systemctl start promotales
```

### Verificar Uso de Memória

```bash
free -h
htop  # Se instalado: sudo apt install htop
```

### Backup do Cache

```bash
# Backup manual
sqlite3 /opt/promotales/data/cache.db ".backup /opt/promotales/data/cache_backup.db"
```

---

## Troubleshooting

### Bot não inicia

```bash
# Ver erro detalhado
sudo journalctl -u promotales -n 50 --no-pager

# Verificar se .env existe e tem token
cat /opt/promotales/.env
```

### Chromium não funciona

```bash
# Testar chromium
chromium-browser --headless --disable-gpu --dump-dom https://google.com

# Se der erro, instalar mais deps
sudo apt install -y libgconf-2-4 libxss1
```

### Memória insuficiente

```bash
# Verificar swap
free -h

# Aumentar swap se necessário
sudo swapoff /swapfile
sudo fallocate -l 4G /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```

### Bot reinicia constantemente

```bash
# Ver últimos crashes
sudo journalctl -u promotales --since "1 hour ago" | grep -i error
```

---

## Checklist Final

- [ ] Instância Oracle Cloud criada e rodando
- [ ] SSH funcionando
- [ ] Python 3.11 instalado
- [ ] Chromium instalado
- [ ] Swap configurado (2GB+)
- [ ] Repositório clonado em `/opt/promotales`
- [ ] Virtual env criado e dependências instaladas
- [ ] Arquivo `.env` com BOT_TOKEN
- [ ] Teste manual funcionou
- [ ] Systemd service criado e habilitado
- [ ] Bot rodando (`systemctl status promotales`)
- [ ] Teste no Telegram funcionando

---

## Custos

Oracle Cloud Free Tier inclui:
- 2 VMs AMD (1 OCPU, 1 GB RAM cada) **OU**
- 1 VM ARM (até 4 OCPUs, 24 GB RAM)
- 200 GB de armazenamento
- 10 TB de transferência/mês

**Custo: R$ 0,00** (se ficar dentro do free tier)

---

*Última atualização: 2026-02-03*
