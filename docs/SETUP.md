# Guia de Configuração - PromoTales Bot

## Pré-requisitos

### Software Necessário

1. **Python 3.8+**
   - Download: https://www.python.org/downloads/
   - Verificar instalação: `python --version`

2. **Google Chrome**
   - Download: https://www.google.com/chrome/
   - Versão mais recente recomendada

3. **Git** (opcional)
   - Download: https://git-scm.com/downloads

## Instalação Passo a Passo

### 1. Clonar ou Baixar o Projeto

**Opção A - Com Git:**
```bash
git clone <url-do-repositorio>
cd PromoTales
```

**Opção B - Download Manual:**
- Baixe o ZIP do projeto
- Extraia para uma pasta
- Abra terminal na pasta

### 2. Criar Ambiente Virtual (Recomendado)

**Windows:**
```bash
python -m venv venv
venv\Scripts\activate
```

**Linux/Mac:**
```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Instalar Dependências

```bash
pip install -r requirements.txt
```

Isso instalará:
- python-telegram-bot
- selenium
- selenium-wire
- python-dotenv
- chromedriver-autoinstaller
- E outras dependências

### 4. Criar Bot no Telegram

1. Abra o Telegram
2. Procure por `@BotFather`
3. Envie `/newbot`
4. Siga as instruções:
   - Escolha um nome (ex: "PromoTales Helper")
   - Escolha um username (ex: "promotales_bot")
5. Copie o TOKEN fornecido

### 5. Configurar Variáveis de Ambiente

Crie um arquivo `.env` na raiz do projeto:

```env
BOT_TOKEN=seu_token_aqui
```

**Exemplo:**
```env
BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz
```

### 6. Verificar ChromeDriver

O ChromeDriver será instalado automaticamente na primeira execução.

**Windows:** Certifique-se que o Chrome está em:
```
C:\Program Files\Google\Chrome\Application\chrome.exe
```

**Linux/Mac:** O caminho será detectado automaticamente.

## Executar o Bot

### Modo Desenvolvimento (Local)

```bash
python main_new.py
```

Você verá algo como:
```
==================================================
Iniciando PromoTales Bot
==================================================
INFO - Chrome configurado para ambiente local
INFO - ChromeDriver iniciado com sucesso
INFO - Handlers configurados
INFO - 🛠️ Bot rodando localmente (modo desenvolvimento)
INFO - ✅ Bot iniciado com sucesso. Aguardando mensagens...
```

### Testar no Telegram

1. Procure seu bot no Telegram
2. Envie `/start`
3. Envie o nome de um item (ex: "Manto da Bruxa")
4. Aguarde a resposta

## Estrutura de Arquivos Após Instalação

```
PromoTales/
├── venv/                    # Ambiente virtual (criado)
├── src/
│   ├── bot/
│   ├── scraper/
│   ├── utils/
│   └── config/
├── tests/
├── docs/
├── .env                     # Suas configurações (criado)
├── main_new.py
├── requirements.txt
└── README.md
```

## Troubleshooting

### Erro: "BOT_TOKEN não encontrado"

**Causa:** Arquivo `.env` não existe ou está incorreto

**Solução:**
1. Verifique se `.env` está na raiz do projeto
2. Confirme que tem a linha `BOT_TOKEN=...`
3. Não use aspas no token

### Erro: "ChromeDriver não encontrado"

**Causa:** Chrome não está instalado ou em local diferente

**Solução Windows:**
1. Instale o Chrome
2. Verifique o caminho em `src/config/settings.py`
3. Ajuste `CHROME_BINARY_LOCAL` se necessário

**Solução Linux:**
```bash
sudo apt-get update
sudo apt-get install -y chromium-browser chromium-chromedriver
```

### Erro: "selenium não encontrado"

**Causa:** Dependências não instaladas

**Solução:**
```bash
pip install -r requirements.txt
```

### Bot não responde no Telegram

**Verificações:**
1. Bot está rodando no terminal?
2. Token está correto?
3. Você iniciou a conversa com `/start`?
4. Verifique logs no terminal

### Erro: "Item não encontrado" para todos os itens

**Possíveis causas:**
1. Site do Ragnatales está fora do ar
2. Estrutura do site mudou
3. Timeout muito curto

**Solução:**
1. Acesse https://ragnatales.com.br/db/items manualmente
2. Aumente timeouts em `src/config/settings.py`
3. Verifique logs para erros específicos

## Deploy em Produção

### Render (Recomendado)

1. Crie conta em https://render.com
2. Crie novo Web Service
3. Conecte seu repositório
4. Configure:
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `python main_new.py`
5. Adicione variável de ambiente:
   - `BOT_TOKEN`: seu token
   - `RENDER`: true

### Heroku

1. Crie conta em https://heroku.com
2. Instale Heroku CLI
3. Configure buildpacks:
```bash
heroku buildpacks:add --index 1 heroku/python
heroku buildpacks:add --index 2 https://github.com/heroku/heroku-buildpack-google-chrome
heroku buildpacks:add --index 3 https://github.com/heroku/heroku-buildpack-chromedriver
```
4. Configure variável:
```bash
heroku config:set BOT_TOKEN=seu_token
```

## Testes

### Executar Testes Unitários

```bash
# Todos os testes
python -m unittest discover tests

# Teste específico
python -m unittest tests.test_config
python -m unittest tests.test_scraper
python -m unittest tests.test_bot
```

## Logs

Logs são salvos em:
- **Console:** Saída padrão
- **Arquivo:** `promotales_bot.log` (criado automaticamente)

### Nível de Logs

Altere em `main_new.py`:
```python
logging.basicConfig(level=logging.DEBUG)  # Mais detalhado
logging.basicConfig(level=logging.INFO)   # Normal
logging.basicConfig(level=logging.WARNING) # Apenas avisos
```

## Próximos Passos

Após configuração bem-sucedida:
1. Leia `ARCHITECTURE.md` para entender o código
2. Veja `README.md` para roadmap de features
3. Contribua com melhorias!

## Suporte

Para problemas não listados aqui:
1. Verifique os logs em `promotales_bot.log`
2. Abra uma issue no GitHub
3. Inclua: versão Python, SO, mensagem de erro completa
