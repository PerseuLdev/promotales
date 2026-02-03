# Plano de Implementação: Arquitetura Local vs Produção

## Visão Geral
Otimizar o PromoTales Bot para diferentes ambientes com melhor performance e escalabilidade.

---

## Fase 1: Cache + Browser Singleton (Local)
**Objetivo:** Reduzir 80% das buscas redundantes

### 1.1 Cache Service
- [x] Criar `src/services/cache_service.py`
  - [x] Classe `CacheEntry` (dataclass para armazenar resultado + timestamp + ttl)
  - [x] Classe abstrata `BaseCache` (interface)
  - [x] Classe `MemoryCache` (implementação em memória)
  - [x] Método `get(item_name)` - busca no cache
  - [x] Método `set(item_name, result, ttl)` - salva no cache
  - [x] Método `invalidate(item_name)` - remove do cache
  - [x] Método `clear()` - limpa todo o cache
  - [x] Método `cleanup()` - remove entradas expiradas
  - [x] Normalização de chaves (lowercase, strip)

### 1.2 Browser Pool (Singleton)
- [x] Criar `src/services/browser_pool.py`
  - [x] Classe `BrowserManager` (singleton)
  - [x] Método `get_browser()` - retorna instância única
  - [x] Método `release_browser()` - marca como disponível
  - [x] Método `restart_if_needed()` - reinicia se com problema
  - [x] Método `shutdown()` - fecha o browser
  - [x] Lock para thread-safety

### 1.3 Atualizar Settings
- [x] Modificar `src/config/settings.py`
  - [x] Adicionar `CACHE_TTL = 300` (5 minutos)
  - [x] Adicionar `BROWSER_POOL_SIZE = 1`
  - [x] Adicionar `MAX_QUEUE_SIZE = 10`
  - [x] Adicionar `ENVIRONMENT` (local/production)

### 1.4 Modificar Scraper
- [x] Modificar `src/scraper/ragnatales_scraper.py`
  - [x] Aceitar browser externo no construtor
  - [x] Não fechar browser se foi passado externamente
  - [x] Adicionar flag `_external_browser`

### 1.5 Integrar no Bot
- [x] Modificar `src/bot/telegram_bot.py`
  - [x] Inicializar `MemoryCache` no startup
  - [x] Inicializar `BrowserManager` no startup
  - [x] Verificar cache antes de buscar
  - [x] Salvar resultado no cache após busca
  - [x] Cleanup no shutdown

### 1.6 Testes Fase 1
- [x] Testar cache hit/miss
- [x] Testar TTL expirando
- [x] Testar browser singleton reutilizado
- [x] Testar múltiplas buscas sequenciais

---

## Fase 2: Fila de Jobs (Local Melhorado)
**Objetivo:** Bot não trava durante buscas

### 2.1 Job Queue Local
- [x] Criar `src/services/job_queue.py`
  - [x] Classe `SearchJob` (dataclass)
  - [x] Classe `LocalJobQueue` (threading.Queue)
  - [x] Método `enqueue(job)` - adiciona à fila
  - [x] Método `dequeue()` - pega próximo job
  - [x] Método `get_result(job_id)` - busca resultado

### 2.2 Search Worker
- [x] Criar `src/services/search_worker.py`
  - [x] Classe `SearchWorker`
  - [x] Worker thread que processa fila
  - [x] Integração com cache e browser pool
  - [x] Callback para notificar resultado

### 2.3 Integrar Fila no Bot
- [x] Modificar `src/bot/telegram_bot.py`
  - [x] Iniciar worker thread no startup
  - [x] Enfileirar buscas ao invés de executar direto
  - [x] Responder "buscando..." imediatamente
  - [x] Editar mensagem quando resultado pronto

### 2.4 Testes Fase 2
- [x] Testar múltiplas buscas enfileiradas
- [x] Testar bot responsivo durante busca
- [x] Testar timeout de jobs

---

## Fase 3: Redis + Pool (Produção)
**Objetivo:** Escalar para múltiplos usuários

### 3.1 Redis Cache
- [ ] Criar `src/services/redis_cache.py`
  - [ ] Classe `RedisCache` (implementa BaseCache)
  - [ ] Conexão com Redis
  - [ ] Serialização/deserialização de resultados
  - [ ] TTL nativo do Redis

### 3.2 Browser Pool Expandido
- [ ] Modificar `src/services/browser_pool.py`
  - [ ] Classe `BrowserPool` (múltiplas instâncias)
  - [ ] Método `acquire()` async - pega browser disponível
  - [ ] Método `release()` async - devolve ao pool
  - [ ] Health check periódico
  - [ ] Configurável via `BROWSER_POOL_SIZE`

### 3.3 Redis Job Queue
- [ ] Modificar `src/services/job_queue.py`
  - [ ] Classe `RedisJobQueue`
  - [ ] Fila persistente no Redis
  - [ ] Múltiplos workers podem consumir

### 3.4 Worker Processes
- [ ] Modificar `src/services/search_worker.py`
  - [ ] Suporte a múltiplos workers
  - [ ] Async/await
  - [ ] Graceful shutdown

### 3.5 Configurações Produção
- [ ] Modificar `src/config/settings.py`
  - [ ] `REDIS_URL` do ambiente
  - [ ] `BROWSER_POOL_SIZE = 3`
  - [ ] `WORKER_COUNT = 2`
  - [ ] `HEADLESS = True`

### 3.6 Atualizar Dependências
- [ ] Modificar `requirements.txt`
  - [ ] Adicionar `redis>=4.0.0`
  - [ ] Adicionar `aioredis>=2.0.0` (opcional)

### 3.7 Testes Fase 3
- [ ] Testar conexão Redis
- [ ] Testar cache distribuído
- [ ] Testar pool de browsers
- [ ] Testar múltiplos workers

---

## Integração com Monitor Service
- [ ] Modificar `src/services/monitor_service.py`
  - [ ] Usar cache compartilhado
  - [ ] Usar browser pool
  - [ ] Não criar nova instância por item

---

## Verificação Final

### Performance Local
- [ ] RAM por busca reduzida (~50MB vs ~300MB)
- [ ] Cache hit < 100ms
- [ ] Browser reutilizado entre buscas

### Performance Produção
- [ ] Múltiplos usuários simultâneos
- [ ] Cache compartilhado funcionando
- [ ] Pool de browsers escalando

---

## Arquivos Criados/Modificados

### Novos
- [x] `src/services/cache_service.py`
- [x] `src/services/browser_pool.py`
- [x] `src/services/job_queue.py`
- [x] `src/services/search_worker.py`
- [ ] `src/services/redis_cache.py` (Fase 3)

### Modificados
- [x] `src/config/settings.py`
- [x] `src/scraper/ragnatales_scraper.py`
- [ ] `src/services/monitor_service.py`
- [x] `src/bot/telegram_bot.py`
- [ ] `requirements.txt`

---

## Progresso

| Fase | Status | Completude |
|------|--------|------------|
| Fase 1 | ✅ Concluída | 100% |
| Fase 2 | ✅ Concluída | 100% |
| Fase 3 | ⏳ Pendente | 0% |

**Última atualização:** 2026-02-03
