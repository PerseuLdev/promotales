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

## Fase 3: SQLite + Oracle Cloud (MVP Produção)
**Objetivo:** Deploy em produção com baixo consumo de memória (1GB RAM)

### 3.1 SQLite Cache (Adaptado de Redis)
- [x] Criar `src/services/sqlite_cache.py`
  - [x] Classe `SQLiteCache` (implementa BaseCache)
  - [x] Tabela com key, value, created_at, ttl
  - [x] Serialização JSON de ItemSearchResult
  - [x] TTL com cleanup automático
  - [x] Thread-safe (connection per thread)
  - [x] Método vacuum() para otimização

### 3.2 Configurações Produção
- [x] Modificar `src/config/settings.py`
  - [x] `IS_ORACLE` detection
  - [x] `CACHE_TYPE` = "sqlite" ou "memory"
  - [x] `SQLITE_DB_PATH` configurável
  - [x] `HEADLESS = True` em produção
  - [x] `get_chrome_binary()` helper

### 3.3 Factory de Cache
- [x] Modificar `src/bot/telegram_bot.py`
  - [x] `create_cache()` factory function
  - [x] Seleciona MemoryCache ou SQLiteCache
  - [x] Logs de ambiente (Oracle/Render/Local)

### 3.4 Scripts de Deploy Oracle Cloud
- [x] Criar `deploy/oracle/setup.sh`
  - [x] Instalação de dependências
  - [x] Configuração de swap (1GB)
  - [x] Instalação do Chromium
- [x] Criar `deploy/oracle/promotales.service`
  - [x] Systemd unit file
  - [x] Limites de memória (700M max)
  - [x] Variáveis de ambiente
- [x] Criar `deploy/oracle/install.sh`
  - [x] Setup do venv
  - [x] Instalação de deps Python
  - [x] Habilitação do systemd
- [x] Criar `deploy/oracle/update.sh`
- [x] Criar `deploy/oracle/backup.sh`

### 3.5 Testes Fase 3
- [x] Testes unitários SQLiteCache
- [x] Testes de serialização
- [x] Testes de thread-safety

### 3.6 Futura Escalabilidade (Hostinger KVM2)
- [ ] Redis Cache (quando tiver 2GB+ RAM)
- [ ] Browser Pool com múltiplas instâncias
- [ ] Múltiplos workers

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
- [x] `src/services/sqlite_cache.py` (Fase 3)
- [x] `deploy/oracle/setup.sh`
- [x] `deploy/oracle/install.sh`
- [x] `deploy/oracle/update.sh`
- [x] `deploy/oracle/backup.sh`
- [x] `deploy/oracle/promotales.service`
- [x] `tests/test_sqlite_cache.py`

### Modificados
- [x] `src/config/settings.py`
- [x] `src/scraper/ragnatales_scraper.py`
- [ ] `src/services/monitor_service.py`
- [x] `src/bot/telegram_bot.py`

---

---

## Fase 4: Sistema de Builds (Futuro)
**Objetivo:** Permitir consulta de preços de builds completas

### 4.1 Estrutura de Dados
- [ ] Criar `data/builds/` diretório
- [ ] Criar CSVs por classe (ex: `knight.csv`, `wizard.csv`)
- [ ] Formato CSV: `build_name,phase,item1,item2,item3,...`
  - `phase`: early, mid, end, high
  - Items separados por vírgula

### 4.2 Build Service
- [ ] Criar `src/services/build_service.py`
  - [ ] Classe `Build` (dataclass)
  - [ ] Classe `BuildService`
  - [ ] Método `list_classes()` - lista classes disponíveis
  - [ ] Método `list_builds(class, phase)` - lista builds filtradas
  - [ ] Método `get_build(build_name)` - retorna build específica
  - [ ] Método `load_builds()` - carrega CSVs

### 4.3 Comandos do Bot
- [ ] `/build` - Lista todas as classes disponíveis
- [ ] `/build <classe>` - Lista builds da classe
- [ ] `/build <classe> <fase>` - Filtra por fase (early/mid/end/high)
- [ ] Botões inline para navegação

### 4.4 Consulta de Preços
- [ ] Buscar preço de cada item da build
- [ ] Usar cache para otimizar
- [ ] Mostrar preço total da build
- [ ] Mostrar itens não encontrados

### 4.5 Formato de Resposta
```
🛡️ Build: Knight Tank End Game

📦 Itens (5):
• +9 Manto da Bruxa - 15.000.000z
• +7 Botas Temporais - 8.500.000z
• Anel Temporal [1] - 25.000.000z
• Escudo Valquíria - 3.200.000z
• Elmo de Odin - 12.000.000z

💰 Total: 63.700.000z
⏱️ Atualizado: agora
```

### 4.6 Exemplo de CSV
```csv
# data/builds/knight.csv
build_name,phase,items
Tank Básico,early,escudo buckler,espada,armadura de couro
Tank Intermediário,mid,escudo valquíria,lança,manto da bruxa
Tank End Game,end,+9 manto da bruxa,+7 botas temporais,anel temporal
MVP Hunter,high,+12 lança das trevas,+10 armadura sagrada,anel celestial
```

### 4.7 Testes Fase 4
- [ ] Testar carregamento de CSVs
- [ ] Testar filtros por classe/fase
- [ ] Testar consulta de preços em lote
- [ ] Testar cache de builds

---

## Progresso

| Fase | Status | Completude |
|------|--------|------------|
| Fase 1 | ✅ Concluída | 100% |
| Fase 2 | ✅ Concluída | 100% |
| Fase 3 | ✅ Concluída | 100% |
| Fase 4 | 📋 Planejado | 0% |

**Última atualização:** 2026-02-03
**Deploy:** Oracle Cloud (1GB RAM) com SQLite
