# PromoTales Bot - Plano de Execução Local

## Status Atual do Projeto

```
Progresso: ████████████████░░░░ 80%

[x] Milestone 1: Arquitetura e Estrutura    - CONCLUIDO
[x] Milestone 2: Qualidade de Codigo        - CONCLUIDO
[ ] Fase Final: Testes e Validacao Local    - EM ANDAMENTO
```

---

## Estrutura Atual do Projeto

```
PromoTales/
├── src/
│   ├── __init__.py
│   ├── bot/
│   │   ├── __init__.py
│   │   └── telegram_bot.py       # Bot Telegram com handlers
│   ├── scraper/
│   │   ├── __init__.py
│   │   └── ragnatales_scraper.py # Web scraper com Selenium
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── chrome_setup.py       # Configuracao ChromeDriver
│   │   ├── validators.py         # Validacao de inputs
│   │   ├── rate_limiter.py       # Rate limiting por usuario
│   │   └── logger.py             # Sistema de logging
│   ├── config/
│   │   ├── __init__.py
│   │   └── settings.py           # Configuracoes centralizadas
│   └── exceptions.py             # Excecoes customizadas
├── tests/
│   ├── __init__.py
│   ├── conftest.py               # Fixtures compartilhadas
│   ├── test_bot.py
│   ├── test_scraper.py
│   ├── test_config.py
│   ├── test_validators.py
│   └── test_rate_limiter.py
├── docs/
│   ├── PLANO_LOCAL.md            # Este documento
│   ├── ARCHITECTURE.md           # Arquitetura tecnica
│   ├── SETUP.md                  # Guia de configuracao
│   └── TESTING.md                # Guia de testes
├── logs/                         # Logs do sistema (gerado)
├── main.py                       # Ponto de entrada
├── requirements.txt              # Dependencias
├── .env                          # Variaveis de ambiente (nao versionado)
├── .gitignore
├── pytest.ini                    # Configuracao pytest
└── README.md                     # Documentacao principal
```

---

## Funcionalidades Implementadas

### Bot do Telegram
- [x] Comando `/start` - Boas-vindas
- [x] Comando `/help` - Ajuda detalhada
- [x] Busca de itens por nome
- [x] Retorno de menor preco + localizacao (@market X/Y)
- [x] Retorno de preco medio
- [x] Mensagens de status ("Buscando...")
- [x] Error handler global

### Web Scraping
- [x] Scraper com Selenium para Ragnatales
- [x] Extracao de precos das lojas
- [x] Extracao de localizacao das lojas
- [x] Context manager para gestao de recursos
- [x] Suporte a ambiente local e cloud

### Qualidade de Codigo
- [x] Type hints em todo o codigo
- [x] Logging estruturado (console + arquivo)
- [x] Validacao de inputs (protecao contra XSS/SQL injection)
- [x] Rate limiting (5 buscas/min por usuario)
- [x] Excecoes customizadas
- [x] Testes unitarios (22+ testes)

---

## Como Rodar Localmente

### Pre-requisitos
- Python 3.8+
- Google Chrome instalado
- Token do bot do Telegram (via @BotFather)

### Instalacao

```bash
# 1. Clone o repositorio (se ainda nao fez)
cd C:\vs_code\PromoTales

# 2. Crie ambiente virtual
python -m venv venv
venv\Scripts\activate  # Windows

# 3. Instale dependencias
pip install -r requirements.txt

# 4. Configure o .env
echo BOT_TOKEN=seu_token_aqui > .env

# 5. Execute o bot
python main.py
```

### Testando

```bash
# Executar todos os testes
pytest tests/ -v

# Com cobertura
pytest tests/ --cov=src --cov-report=html

# Teste especifico
pytest tests/test_validators.py -v
```

### Verificando Logs

```bash
# Windows
type logs\promotales.log

# Ultimas linhas
powershell -Command "Get-Content logs\promotales.log -Tail 50"
```

---

## Configuracoes Importantes

### Arquivo .env
```env
BOT_TOKEN=seu_token_do_telegram
```

### Rate Limiting (src/config/settings.py)
```python
MAX_REQUESTS_PER_MINUTE = 5   # Maximo de buscas por minuto
RATE_LIMIT_WINDOW = 60        # Janela em segundos
```

### Timeouts (src/config/settings.py)
```python
PAGE_LOAD_TIMEOUT = 5         # Timeout para carregar pagina
SEARCH_TIMEOUT = 3            # Timeout para busca
SHOPS_TIMEOUT = 3             # Timeout para lojas
```

---

## O Que Falta Para Versao Local Funcional

### Pendente (Prioridade Alta)
- [ ] Testar bot end-to-end localmente
- [ ] Verificar se ChromeDriver esta funcionando
- [ ] Validar busca de itens no Ragnatales
- [ ] Corrigir bugs encontrados nos testes

### Opcional (Pode Ser Feito Depois)
- [ ] Cache de resultados (TTL 5 min)
- [ ] SQLite para historico de precos
- [ ] Mais testes de integracao

---

## Checklist de Validacao Local

Antes de considerar a versao local "pronta":

### Funcional
- [ ] Bot inicia sem erros
- [ ] Comando /start funciona
- [ ] Comando /help funciona
- [ ] Busca de item retorna resultado
- [ ] Rate limiting bloqueia apos 5 buscas
- [ ] Logs sao gravados corretamente

### Qualidade
- [ ] Todos os testes passam (`pytest tests/ -v`)
- [ ] Cobertura >= 70%
- [ ] Nenhum erro no console

### Experiencia do Usuario
- [ ] Mensagens sao claras e informativas
- [ ] Erros sao tratados com mensagens amigaveis
- [ ] Tempo de resposta < 15 segundos

---

## Troubleshooting

### "BOT_TOKEN nao encontrado"
Crie arquivo `.env` com: `BOT_TOKEN=seu_token`

### "ChromeDriver nao encontrado"
- Instale Google Chrome
- ChromeDriver sera instalado automaticamente pelo `chromedriver-autoinstaller`

### "Item nao encontrado" para todos os itens
- Verifique conexao com internet
- O site do Ragnatales pode estar fora do ar
- Tente aumentar timeouts em `settings.py`

### Bot nao responde
- Verifique se o bot esta rodando no terminal
- Verifique se o token esta correto
- Veja os logs em `logs/promotales.log`

---

## Proximos Passos (Apos Versao Local Funcionar)

Quando a versao local estiver estavel e testada, consultar:
- `docs/plano-escala.md` - Para deploy em producao/VPS

---

## Comandos Uteis

```bash
# Executar bot
python main.py

# Executar testes
pytest tests/ -v

# Ver estrutura do projeto
tree /F src  # Windows

# Verificar imports
python -c "from src.bot import TelegramBot; print('OK')"

# Limpar cache Python
del /S /Q __pycache__  # Windows
```

---

**Data:** Janeiro 2026
**Versao:** Local 1.0
**Status:** Em desenvolvimento
