# Arquitetura do PromoTales Bot

## Visão Geral

O PromoTales Bot é uma aplicação Python modular que integra um bot do Telegram com web scraping do site Ragnatales para fornecer informações de preços de itens do jogo.

## Estrutura de Módulos

### 1. `src/config/`
**Responsabilidade**: Configurações centralizadas da aplicação

- `settings.py`: Classe `Settings` com todas as configurações
  - Tokens e credenciais
  - URLs e endpoints
  - Timeouts e configurações de performance
  - Detecção de ambiente (local vs cloud)

### 2. `src/utils/`
**Responsabilidade**: Utilitários e funções auxiliares

- `chrome_setup.py`: Configuração do Selenium WebDriver
  - `setup_chrome_options()`: Configura opções do Chrome
  - `setup_chrome_service()`: Configura o ChromeDriver
  - `setup_chrome_driver()`: Retorna driver configurado

### 3. `src/scraper/`
**Responsabilidade**: Web scraping do Ragnatales

- `ragnatales_scraper.py`: Classe `RagnatalesScraper`
  - `_search_item()`: Busca item no site
  - `_get_average_price()`: Extrai preço médio
  - `_get_shops_data()`: Extrai dados das lojas
  - `get_item_info()`: Método público principal
  - Context manager para gerenciamento de recursos

### 4. `src/bot/`
**Responsabilidade**: Interface com Telegram

- `telegram_bot.py`: Classe `TelegramBot`
  - `start_command()`: Handler do /start
  - `help_command()`: Handler do /help
  - `handle_message()`: Handler de mensagens (busca de itens)
  - `error_handler()`: Handler de erros globais
  - `setup_handlers()`: Configura todos os handlers
  - `run()`: Inicia o bot

## Fluxo de Dados

```
Usuário (Telegram)
    ↓
TelegramBot
    ↓
RagnatalesScraper
    ↓
Chrome/Selenium
    ↓
Ragnatales.com.br
    ↓
Chrome/Selenium
    ↓
RagnatalesScraper (processamento)
    ↓
TelegramBot (formatação)
    ↓
Usuário (Telegram)
```

## Fluxo de Execução

1. **Inicialização**
   - `main.py` importa e cria `TelegramBot`
   - `TelegramBot.__init__()` valida configurações
   - Cria instância de `RagnatalesScraper`
   - Configura handlers do Telegram

2. **Busca de Item**
   - Usuário envia mensagem com nome do item
   - `handle_message()` valida entrada
   - `scraper.get_item_info()` é chamado
   - Scraper inicia ChromeDriver
   - Navega e extrai informações
   - Retorna dados formatados
   - Bot envia resposta ao usuário

3. **Finalização**
   - ChromeDriver é fechado automaticamente
   - Recursos são liberados

## Padrões de Projeto

### 1. Singleton (implícito)
- `Settings`: Uma única instância de configurações

### 2. Context Manager
- `RagnatalesScraper`: Gerencia ciclo de vida do driver
```python
with RagnatalesScraper() as scraper:
    result = scraper.get_item_info("item")
```

### 3. Separation of Concerns
- Cada módulo tem responsabilidade única e bem definida
- Bot não conhece detalhes de scraping
- Scraper não conhece detalhes do Telegram

### 4. Dependency Injection
- Configurações injetadas via `Settings`
- Facilita testes e manutenção

## Tratamento de Erros

### Níveis de Tratamento

1. **Nível de Scraping**
   - Erros de navegação
   - Elementos não encontrados
   - Timeout de página

2. **Nível de Bot**
   - Validação de entrada
   - Erros de comunicação com Telegram
   - Erros de processamento

3. **Nível de Aplicação**
   - Erros fatais de inicialização
   - Interrupção por usuário

### Estratégia de Logs

- `INFO`: Operações normais e eventos importantes
- `WARNING`: Situações inesperadas mas recuperáveis
- `ERROR`: Erros que impedem operação específica
- `CRITICAL`: Erros fatais da aplicação

## Considerações de Performance

### Scraping
- Timeouts configuráveis
- Driver reutilizável (futuramente)
- Modo headless para economia de recursos

### Bot
- Respostas assíncronas
- Mensagens de feedback ao usuário
- Validação antes de processamento pesado

## Segurança

1. **Credenciais**
   - Variáveis de ambiente (.env)
   - Nunca versionadas no git

2. **Validação de Entrada**
   - Sanitização de nomes de itens
   - Limite de tamanho de mensagens

3. **Rate Limiting**
   - A ser implementado (Milestone 3)

## Escalabilidade

### Atual
- Single-threaded
- Um usuário por vez

### Futuro (Roadmap)
- Pool de drivers
- Cache de resultados
- Processamento paralelo
- Queue de requisições

## Ambientes

### Desenvolvimento Local
- Chrome visível (opcional)
- Logs detalhados
- ChromeDriver local

### Produção (Render)
- Chrome headless
- Logs otimizados
- ChromeDriver auto-instalado
- Variáveis de ambiente gerenciadas

## Testes

### Estrutura
- `tests/test_config.py`: Testes de configuração
- `tests/test_scraper.py`: Testes de scraping
- `tests/test_bot.py`: Testes do bot

### Tipos
- Unitários: Funções isoladas
- Integração: Fluxos completos (futuro)
- E2E: Teste completo usuário-bot (futuro)

## Manutenção

### Pontos de Atenção
1. **Seletores CSS/XPath**
   - Podem mudar se o site for atualizado
   - Localizados em `ragnatales_scraper.py`

2. **Timeouts**
   - Ajustar conforme velocidade da rede
   - Configurados em `settings.py`

3. **Formato de Preços**
   - Regex de parsing em `ragnatales_scraper.py`
   - Formato de saída em `telegram_bot.py`

## Próximos Passos

Ver `README.md` seção Roadmap para features planejadas.
