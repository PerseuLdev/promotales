# Plano de Escala - PromoTales Bot

## Milestones e Paralelização

```
LEGENDA:
  ■ = Milestone
  → = Dependência (precisa completar antes)
  ⇄ = Pode ser paralelizado

TIMELINE:

  Semana 1                          Semana 2                          Semana 3                          Semana 4
  ───────────────────────────────────────────────────────────────────────────────────────────────────────────────

  ■ M1: Scraping Leve ──────────────┐
                                    ├──→ ■ M4: Sistema de Filas ──→ ■ M6: Watchlist ──┐
  ■ M2: Database SQLite ────────────┘                              ⇄                  ├──→ ■ M8: Alertas
                                                                   ■ M7: Batch ───────┘
  ■ M3: Memory Fixes ──────────────────────────────────────────────┘

                                    ■ M5: Scheduler ───────────────────────────────────┘

  ■ M9: Stripe + Pagamentos ────────────────────────────────────────────────────────────→ (paralelo com tudo)


PARALELIZAÇÃO POSSÍVEL:

  [Paralelo A] M1 + M2 + M3 + M9 (Semana 1-2)
  [Paralelo B] M4 + M5 + M9 (Semana 2)
  [Paralelo C] M6 + M7 + M9 (Semana 3)
  [Paralelo D] M8 + finalização M9 (Semana 4)
```

---

## Milestones Detalhadas

### M1: Scraping Leve (BeautifulSoup)
**Duração estimada**: 2-3 dias
**Dependências**: Nenhuma
**Pode paralelizar com**: M2, M3, M9

**Tarefas:**
- [ ] Analisar HTML do Ragnatales (verificar se dados estão server-side)
- [ ] Criar `src/scraper/lightweight_scraper.py`
- [ ] Implementar busca com requests + BeautifulSoup
- [ ] Criar `src/scraper/scraper_factory.py` (fallback para Chrome)
- [ ] Testes unitários

**Critério de sucesso**: Busca retorna preço em < 5 segundos, RAM < 100MB

**Arquivos:**
```
src/scraper/lightweight_scraper.py  (NOVO)
src/scraper/scraper_factory.py      (NOVO)
tests/test_lightweight_scraper.py   (NOVO)
```

---

### M2: Database SQLite
**Duração estimada**: 2-3 dias
**Dependências**: Nenhuma
**Pode paralelizar com**: M1, M3, M9

**Tarefas:**
- [ ] Criar estrutura `src/database/`
- [ ] Definir schema completo (users, products, price_history, watchlist, plans, subscriptions)
- [ ] Implementar migrations
- [ ] Criar repository com CRUD operations
- [ ] Configurar WAL mode para melhor concorrência
- [ ] Testes unitários

**Critério de sucesso**: CRUD funcionando, dados persistem após restart

**Arquivos:**
```
src/database/__init__.py
src/database/schema.py
src/database/repository.py
src/database/migrations/v1_initial.sql
data/promotales.db (gerado)
tests/test_database.py (NOVO)
```

**Schema Completo:**
```sql
-- Usuarios
CREATE TABLE users (
    id INTEGER PRIMARY KEY,
    telegram_id INTEGER UNIQUE NOT NULL,
    username TEXT,
    email TEXT,
    plan TEXT DEFAULT 'free',
    stripe_customer_id TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    last_active DATETIME
);

-- Configuracao de planos
CREATE TABLE plans (
    name TEXT PRIMARY KEY,
    display_name TEXT NOT NULL,
    price_cents INTEGER NOT NULL,
    stripe_price_id TEXT,
    watchlist_limit INTEGER,
    batch_limit INTEGER,
    priority INTEGER,
    alerts_per_day INTEGER
);

INSERT INTO plans VALUES
    ('free', 'Grátis', 0, NULL, 5, 5, 3, 10),
    ('basic', 'Básico', 990, 'price_xxx', 20, 20, 2, 50),
    ('premium', 'Premium', 2490, 'price_yyy', 50, 50, 1, -1);

-- Subscriptions (assinaturas ativas)
CREATE TABLE subscriptions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    plan_name TEXT NOT NULL,
    stripe_subscription_id TEXT UNIQUE,
    status TEXT DEFAULT 'active',  -- active, canceled, past_due, trialing
    current_period_start DATETIME,
    current_period_end DATETIME,
    cancel_at_period_end BOOLEAN DEFAULT FALSE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME,
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (plan_name) REFERENCES plans(name)
);

-- Historico de pagamentos
CREATE TABLE payments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    subscription_id INTEGER,
    stripe_payment_intent_id TEXT UNIQUE,
    stripe_invoice_id TEXT,
    amount_cents INTEGER NOT NULL,
    currency TEXT DEFAULT 'brl',
    status TEXT NOT NULL,  -- succeeded, pending, failed
    payment_method TEXT,   -- card, pix
    paid_at DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (subscription_id) REFERENCES subscriptions(id)
);

-- Produtos rastreados
CREATE TABLE products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    normalized_name TEXT NOT NULL,
    last_price REAL,
    last_location TEXT,
    last_checked DATETIME,
    total_searches INTEGER DEFAULT 0
);

-- Historico de precos
CREATE TABLE price_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id INTEGER NOT NULL,
    lowest_price REAL NOT NULL,
    average_price REAL,
    location TEXT,
    recorded_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (product_id) REFERENCES products(id)
);

-- Watchlist
CREATE TABLE watchlist (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    product_id INTEGER NOT NULL,
    target_price REAL,
    alert_threshold REAL DEFAULT 0.05,
    is_active BOOLEAN DEFAULT TRUE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    last_alerted DATETIME,
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (product_id) REFERENCES products(id),
    UNIQUE(user_id, product_id)
);

-- Indexes
CREATE INDEX idx_users_telegram ON users(telegram_id);
CREATE INDEX idx_users_stripe ON users(stripe_customer_id);
CREATE INDEX idx_subscriptions_user ON subscriptions(user_id, status);
CREATE INDEX idx_subscriptions_stripe ON subscriptions(stripe_subscription_id);
CREATE INDEX idx_payments_user ON payments(user_id);
CREATE INDEX idx_watchlist_user ON watchlist(user_id, is_active);
CREATE INDEX idx_watchlist_product ON watchlist(product_id);
CREATE INDEX idx_price_history_product ON price_history(product_id, recorded_at);
```

---

### M3: Memory Fixes
**Duração estimada**: 1 dia
**Dependências**: Nenhuma
**Pode paralelizar com**: M1, M2, M9

**Tarefas:**
- [ ] Corrigir memory leak no rate_limiter.py (cleanup de usuários inativos)
- [ ] Adicionar memory_manager.py para monitoramento
- [ ] Otimizar chrome_setup.py com flags de baixa memória
- [ ] Documentar configuração de swap no VPS

**Critério de sucesso**: Sem crescimento de memória após 1000 requests simulados

**Arquivos:**
```
src/utils/rate_limiter.py      (MODIFICAR)
src/utils/chrome_setup.py      (MODIFICAR)
src/utils/memory_manager.py    (NOVO)
docs/vps-setup.md              (NOVO)
```

---

### M4: Sistema de Filas
**Duração estimada**: 2-3 dias
**Dependências**: M1 ou M2 (precisa de pelo menos um)
**Pode paralelizar com**: M5, M9

**Tarefas:**
- [ ] Criar `src/queue/request_queue.py` com prioridade
- [ ] Implementar worker que processa fila sequencialmente
- [ ] Integrar cache de resultados (5min TTL)
- [ ] Conectar scraper à fila
- [ ] Prioridade baseada no plano do usuário
- [ ] Feedback de posição na fila para usuário

**Critério de sucesso**: Requisições processadas em ordem de prioridade, sem concorrência

**Arquivos:**
```
src/queue/__init__.py
src/queue/request_queue.py     (NOVO)
src/queue/worker.py            (NOVO)
src/queue/cache.py             (NOVO)
tests/test_queue.py            (NOVO)
```

---

### M5: Scheduler (APScheduler)
**Duração estimada**: 2 dias
**Dependências**: M2 (database para watchlist)
**Pode paralelizar com**: M4, M9

**Tarefas:**
- [ ] Adicionar APScheduler ao requirements
- [ ] Criar `src/scheduler/price_monitor.py`
- [ ] Job que roda a cada 30 minutos
- [ ] Busca items únicos de todas as watchlists
- [ ] Integração com fila (prioridade BAIXA)

**Critério de sucesso**: Job executa no intervalo, itens são buscados

**Arquivos:**
```
src/scheduler/__init__.py
src/scheduler/price_monitor.py  (NOVO)
requirements.txt                (MODIFICAR - adicionar APScheduler)
```

---

### M6: Comandos Watchlist
**Duração estimada**: 2 dias
**Dependências**: M2, M4
**Pode paralelizar com**: M7, M9

**Tarefas:**
- [ ] Criar handler para /watch, /unwatch, /watchlist
- [ ] Validar limites baseado no plano do usuário
- [ ] Criar handler para /plano (ver plano atual)
- [ ] Integrar com database repository
- [ ] Mensagens formatadas

**Comandos:**
```
/watch <item> [preco]  - Adiciona item à watchlist
/unwatch <item>        - Remove da watchlist
/watchlist             - Lista itens monitorados
/plano                 - Mostra plano atual e limites
```

**Critério de sucesso**: CRUD de watchlist via Telegram funcionando

**Arquivos:**
```
src/bot/handlers/__init__.py
src/bot/handlers/watchlist_handler.py  (NOVO)
src/bot/handlers/plan_handler.py       (NOVO)
src/bot/telegram_bot.py                (MODIFICAR - registrar handlers)
```

---

### M7: Busca em Lote
**Duração estimada**: 2 dias
**Dependências**: M4 (sistema de filas)
**Pode paralelizar com**: M6, M9

**Tarefas:**
- [ ] Criar conversation handler para /batch
- [ ] Receber lista de itens (um por linha)
- [ ] Validar limite baseado no plano
- [ ] Enfileirar com prioridade MÉDIA
- [ ] Mostrar progresso em tempo real
- [ ] Agregar resultados no final

**Critério de sucesso**: Busca de 10 itens com feedback de progresso

**Arquivos:**
```
src/bot/handlers/batch_handler.py  (NOVO)
src/queue/batch_processor.py       (NOVO)
```

---

### M8: Sistema de Alertas
**Duração estimada**: 2 dias
**Dependências**: M5, M6
**Pode paralelizar com**: M9

**Tarefas:**
- [ ] Criar `src/scheduler/alert_service.py`
- [ ] Detectar queda de preço > threshold
- [ ] Detectar preço alvo atingido
- [ ] Cooldown de 6h entre alertas
- [ ] Respeitar limite de alertas/dia por plano
- [ ] Mensagens formatadas com comparação de preço

**Critério de sucesso**: Alerta enviado quando preço cai

**Arquivos:**
```
src/scheduler/alert_service.py  (NOVO)
```

---

### M9: Sistema de Pagamento (Stripe)
**Duração estimada**: 4-5 dias
**Dependências**: M2 (database para users/subscriptions)
**Pode paralelizar com**: M1, M3, M4, M5, M6, M7, M8 (independente da maioria)

**Decisões:**
- Gateway: **Stripe**
- Ativação: **Automática via Webhook**
- Métodos: **PIX + Cartão**

**Tarefas:**

#### 9.1 Setup Stripe (Dia 1)
- [ ] Criar conta Stripe e obter API keys
- [ ] Configurar produtos e preços no Stripe Dashboard
- [ ] Criar Price IDs para cada plano (basic, premium)
- [ ] Habilitar PIX no Stripe

#### 9.2 Backend Integration (Dia 2-3)
- [ ] Criar `src/payments/__init__.py`
- [ ] Criar `src/payments/stripe_service.py`
  - Criar Customer
  - Criar Checkout Session
  - Criar Subscription
  - Cancelar Subscription
  - Verificar status
- [ ] Criar `src/payments/webhook_handler.py`
  - Handler para `checkout.session.completed`
  - Handler para `invoice.paid`
  - Handler para `invoice.payment_failed`
  - Handler para `customer.subscription.updated`
  - Handler para `customer.subscription.deleted`

#### 9.3 Webhook Server (Dia 3)
- [ ] Criar endpoint Flask para receber webhooks
- [ ] Validar assinatura do webhook (Stripe signature)
- [ ] Atualizar database com status do pagamento
- [ ] Ativar/desativar plano automaticamente

#### 9.4 Bot Commands (Dia 4)
- [ ] `/assinar` - Gera link de checkout Stripe
- [ ] `/cancelar` - Cancela assinatura no fim do período
- [ ] `/fatura` - Mostra próxima cobrança
- [ ] Atualizar `/plano` para mostrar status da assinatura

#### 9.5 Testes e Modo Sandbox (Dia 5)
- [ ] Testar fluxo completo em modo teste
- [ ] Testar webhooks com Stripe CLI
- [ ] Testar PIX e cartão
- [ ] Testar cancelamento e reativação

**Fluxo de Assinatura:**
```
1. Usuário: /assinar basic
2. Bot: Gera Checkout Session com success_url e cancel_url
3. Bot: Envia link de pagamento
4. Usuário: Paga via PIX ou Cartão
5. Stripe: Envia webhook checkout.session.completed
6. Server: Atualiza user.plan = 'basic' no database
7. Bot: Notifica usuário "Plano ativado!"
```

**Fluxo de Renovação:**
```
1. Stripe: Cobra automaticamente no período
2. Stripe: Envia webhook invoice.paid
3. Server: Atualiza subscription.current_period_end
4. (Se falhar) Stripe: Envia invoice.payment_failed
5. Server: Marca subscription.status = 'past_due'
6. Bot: Notifica usuário sobre problema no pagamento
```

**Arquivos:**
```
src/payments/__init__.py
src/payments/stripe_service.py     (NOVO)
src/payments/webhook_handler.py    (NOVO)
src/payments/subscription_manager.py (NOVO)
src/bot/handlers/subscription_handler.py (NOVO)
src/api/webhook_server.py          (NOVO - Flask endpoint)
requirements.txt                    (MODIFICAR - adicionar stripe)
.env                                (MODIFICAR - adicionar STRIPE_* keys)
```

**Variáveis de Ambiente:**
```
STRIPE_SECRET_KEY=sk_test_xxx
STRIPE_PUBLISHABLE_KEY=pk_test_xxx
STRIPE_WEBHOOK_SECRET=whsec_xxx
STRIPE_PRICE_BASIC=price_xxx
STRIPE_PRICE_PREMIUM=price_yyy
WEBHOOK_BASE_URL=https://seu-dominio.com
```

**Comandos Novos:**
```
/assinar [plano]    - Inicia processo de assinatura
/cancelar           - Cancela assinatura (fim do período)
/fatura             - Mostra próxima cobrança e histórico
/plano              - (atualizado) Mostra plano + status assinatura
```

---

## Diagrama de Dependências Atualizado

```
         ┌─────┐
         │ M1  │ Scraping Leve
         └──┬──┘
            │
            ├─────────────────────┐
            ▼                     ▼
         ┌─────┐              ┌─────┐
         │ M4  │◄─────────────│ M2  │ Database
         └──┬──┘              └──┬──┘
            │                    │
    ┌───────┼───────┐            │
    ▼       ▼       ▼            ▼
 ┌─────┐ ┌─────┐ ┌─────┐     ┌─────┐
 │ M6  │ │ M7  │ │ M5  │◄────│ M9  │ Pagamentos
 └──┬──┘ └─────┘ └──┬──┘     └──┬──┘
    │               │           │
    └───────┬───────┘           │
            ▼                   │
         ┌─────┐                │
         │ M8  │ Alertas ◄──────┘ (limites por plano)
         └─────┘


         ┌─────┐
         │ M3  │ Memory Fixes (independente)
         └─────┘


NOTA: M9 (Pagamentos) pode ser desenvolvido em paralelo
      pois só precisa de M2 (Database) pronto.
      Integração com limites acontece no final.
```

---

## Cronograma com Paralelização (4 semanas)

### Semana 1: Fundação

| Dia | Dev 1 (Core) | Dev 2 (Pagamentos) |
|-----|--------------|-------------------|
| 1 | M1: Analisar HTML Ragnatales | M9: Setup Stripe + Dashboard |
| 2 | M1: Implementar BS4 scraper | M2: Estrutura database |
| 3 | M1: Testes + fallback Chrome | M2: Schema completo |
| 4 | M3: Corrigir rate limiter | M2: Repository + testes |
| 5 | M3: Memory manager | M9: stripe_service.py |

**Entregáveis:**
- Scraper leve funcionando
- Database com schema de pagamentos
- Memory leak corrigido
- Stripe service básico

---

### Semana 2: Core + Webhooks

| Dia | Dev 1 (Core) | Dev 2 (Pagamentos) |
|-----|--------------|-------------------|
| 1 | M4: Request queue | M9: webhook_handler.py |
| 2 | M4: Worker + cache | M9: Flask webhook server |
| 3 | M4: Integração bot | M9: Testar webhooks Stripe CLI |
| 4 | M5: Setup APScheduler | M9: subscription_manager.py |
| 5 | M5: Price monitor job | M9: Testes sandbox |

**Entregáveis:**
- Sistema de filas funcionando
- Scheduler configurado
- Webhooks Stripe funcionando
- Assinaturas sendo criadas/canceladas

---

### Semana 3: Features de Usuário

| Dia | Dev 1 (Core) | Dev 2 (Pagamentos) |
|-----|--------------|-------------------|
| 1 | M6: /watch /unwatch | M9: /assinar handler |
| 2 | M6: /watchlist | M9: /cancelar /fatura handlers |
| 3 | M7: /batch handler | M9: Atualizar /plano |
| 4 | M7: Progresso tempo real | M9: Notificações automáticas |
| 5 | M6/M7: Testes | M9: Testes E2E pagamento |

**Entregáveis:**
- Comandos watchlist
- Busca em lote
- Comandos de assinatura
- Fluxo completo de pagamento

---

### Semana 4: Alertas + Integração + Deploy

| Dia | Dev 1 | Dev 2 |
|-----|-------|-------|
| 1 | M8: Alert service | Integrar limites com planos |
| 2 | M8: Cooldown + limites | Testes integração |
| 3 | M8: Testes | Documentação |
| 4 | Testes E2E completos | Configurar VPS |
| 5 | Deploy + Monitoramento | Go Live! |

**Entregáveis:**
- Sistema de alertas
- Limites respeitando planos pagos
- Deploy em produção
- Monitoramento ativo

---

## Resumo de Paralelização

| Paralelo | Milestones | Razão |
|----------|------------|-------|
| A | M1 + M2 + M3 | Sem dependências entre si (fundação) |
| B | M9 em paralelo com tudo | Só precisa de M2, pode evoluir independente |
| C | M4 + M5 | Ambos precisam de M1/M2 prontos |
| D | M6 + M7 | Ambos precisam de M4 |
| E | M8 + finalização M9 | Integrar limites de plano nos alertas |

**Se desenvolvimento solo:** ~20 dias úteis
**Se paralelo (2 devs):** ~15 dias úteis (4 semanas)

---

## Estrutura Final do Projeto

```
PromoTales/
├── src/
│   ├── bot/
│   │   ├── telegram_bot.py
│   │   └── handlers/
│   │       ├── search_handler.py
│   │       ├── batch_handler.py
│   │       ├── watchlist_handler.py
│   │       ├── plan_handler.py
│   │       └── subscription_handler.py   # NOVO
│   ├── scraper/
│   │   ├── lightweight_scraper.py
│   │   ├── ragnatales_scraper.py
│   │   └── scraper_factory.py
│   ├── queue/
│   │   ├── request_queue.py
│   │   ├── worker.py
│   │   ├── cache.py
│   │   └── batch_processor.py
│   ├── scheduler/
│   │   ├── price_monitor.py
│   │   └── alert_service.py
│   ├── payments/                          # NOVO
│   │   ├── __init__.py
│   │   ├── stripe_service.py
│   │   ├── webhook_handler.py
│   │   └── subscription_manager.py
│   ├── api/                               # NOVO
│   │   └── webhook_server.py
│   ├── database/
│   │   ├── schema.py
│   │   └── repository.py
│   ├── utils/
│   │   ├── chrome_setup.py
│   │   ├── rate_limiter.py
│   │   └── memory_manager.py
│   └── config/
│       └── settings.py
├── data/
│   └── promotales.db
├── main.py                                # Bot principal
├── webhook.py                             # NOVO - Webhook server
└── requirements.txt
```

---

## Dependências Atualizadas

```txt
# requirements.txt

# Bot do Telegram
python-telegram-bot==20.7

# Web Scraping
requests>=2.31.0
beautifulsoup4>=4.12.0
lxml>=5.0.0
selenium==4.15.2  # fallback

# Database
# sqlite3 (built-in)

# Scheduler
APScheduler>=3.10.0

# Pagamentos
stripe>=7.0.0

# Web Server (webhooks)
flask>=2.3.0
gunicorn>=21.0.0

# System monitoring
psutil>=5.9.0

# Utilities
python-dotenv==1.0.0
chromedriver-autoinstaller==0.6.3
```

---

## Checklist de Verificação Final

### Core
- [ ] Memória estável < 700MB em uso constante
- [ ] Busca simples < 10s (BS4) ou < 20s (Chrome)
- [ ] Busca em lote funciona com 10+ itens
- [ ] Watchlist respeita limites do plano
- [ ] Alertas enviados quando preço cai > 5%
- [ ] 3+ usuários simultâneos sem crash
- [ ] Dados persistem após restart

### Pagamentos
- [ ] Checkout Stripe gera link corretamente
- [ ] PIX funciona no checkout
- [ ] Cartão funciona no checkout
- [ ] Webhook ativa plano automaticamente
- [ ] Cancelamento funciona no fim do período
- [ ] Renovação automática funciona
- [ ] Falha de pagamento notifica usuário
- [ ] /plano mostra status correto da assinatura

### Infraestrutura
- [ ] Swap configurado no VPS
- [ ] Webhook server rodando (porta separada)
- [ ] HTTPS configurado para webhooks
- [ ] Logs sem erros em 24h de operação
- [ ] Backup do SQLite configurado
