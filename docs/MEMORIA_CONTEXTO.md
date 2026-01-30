# PromoTales Bot - Memoria de Contexto

## Status Atual: 95% Completo

---

## O Que Foi Implementado

### 1. Estrutura do Projeto
```
PromoTales/
├── src/
│   ├── bot/
│   │   └── telegram_bot.py      # Bot com botoes inline e cache
│   ├── scraper/
│   │   └── ragnatales_scraper.py # Scraper com undetected-chromedriver
│   ├── models/
│   │   └── item_offer.py        # Modelos ItemOffer e ItemSearchResult
│   ├── utils/
│   │   ├── chrome_setup.py      # Configuracao Chrome anti-deteccao
│   │   ├── validators.py
│   │   ├── rate_limiter.py
│   │   └── logger.py
│   ├── config/
│   │   └── settings.py
│   └── exceptions.py
├── tests/                        # 58 testes passando
├── main.py                       # Ponto de entrada
└── requirements.txt              # Inclui undetected-chromedriver
```

### 2. Funcionalidades de Equipamentos (COMPLETO)
- Busca por nome: `manto da bruxa`
- Busca com refinamento: `+9 manto da bruxa` ou `manto da bruxa +9`
- Extrai: nome, preco, localizacao, refinamento, cartas, bonus aleatorios
- Botoes inline para filtrar refinamento: +0, +4, +6, +7, +9, +10, etc
- Cache de buscas por usuario (nao precisa buscar de novo ao clicar botao)
- Mostra sempre a loja mais barata

### 3. Tecnologias
- `undetected-chromedriver` para passar verificacao Cloudflare
- Chrome versao 144 (sem headless para passar Cloudflare local)
- `python-telegram-bot` para o bot
- Timeouts configurados em settings.py (PAGE_LOAD=15s)

---

## O Que Foi Implementado Recentemente (30/01/2026)

### Suporte a Itens Nao-Equipamentos (COMPLETO)
Itens como "Folha Afiada", "Elunium", consumiveis, cartas, pets, municoes agora sao suportados.

**Tipos testados:**
| TIPO | QTD | REFINO | CARTAS | BONUS |
|------|-----|--------|--------|-------|
| Consumiveis | SIM | NAO | NAO | NAO |
| Cartas | SIM | NAO | NAO | NAO |
| Pets | NAO | NAO | NAO | NAO |
| ETC | SIM | NAO | NAO | NAO |
| Municoes | SIM | NAO | NAO | NAO |
| Equipamentos | NAO | SIM | SIM | SIM |

**Deteccao automatica de tipo:**
- `ItemOffer.is_equipamento` / `ItemOffer.is_item_simples`
- `ItemSearchResult.is_equipamento()` / `ItemSearchResult.is_item_simples()`
- Baseado na estrutura: quantidade > 1, sem refinamento/cartas/bonus = item simples

**Novos campos:**
- `ItemOffer.quantidade` - quantidade disponivel na loja
- `ItemSearchResult.volume_vendas` - vendas nos ultimos 45 dias
- `ItemSearchResult.quantidade_total()` - soma de todas as ofertas

**Exemplo de resposta para item simples:**
```
🔍 Folha Afiada
📦 7 ofertas encontradas

💰 Mais barato: 5.998z
📍 @market 170/302
📦 Qtd nesta loja: 27 un
🏪 Total no market: 6.587 un

📊 Media 45d: 3.719 zenys
📈 Vendas 45d: 125.291
```

## O Que Falta Implementar

### 1. Historico de Precos (Opcional)
A tabela de historico diario esta disponivel na pagina mas ainda nao e extraida.
Estrutura: DATA | REF. | CARTAS | BONUS | QTD. | MIN. | MEDIO | MAX. | TOTAL

### 2. Testes Unitarios para Novos Modulos
Cobertura atual: 56% (abaixo de 70%)
- Testar `_parse_simple_item()` e `_parse_equipment()`
- Testar `_detect_simple_item()`
- Testar `_get_sales_volume()`

---

## URLs de Exemplo

- Equipamento: https://ragnatales.com.br/db/items/20908 (Manto da Bruxa)
- Nao-equipamento: https://ragnatales.com.br/db/items/7100 (Folha Afiada)

---

## Comandos Uteis

```bash
# Iniciar bot
python main.py

# Executar testes
pytest tests/ -v

# Testar scraper
python -c "
from src.scraper import RagnatalesScraper
scraper = RagnatalesScraper()
result = scraper.search_item('manto da bruxa')
print(result.resumo())
"
```

---

## Problemas Conhecidos

1. `WinError 6` ao fechar ChromeDriver - bug do undetected-chromedriver no Windows, nao afeta funcionamento
2. Cloudflare bloqueia modo headless - por isso usa modo normal localmente
3. Cobertura de testes em 61% (abaixo de 70%) - novos modulos sem testes

---

## Proximos Passos

1. ~~Analisar estrutura de mais itens nao-equipamentos~~ FEITO
2. ~~Implementar extracao para itens nao-equipamentos~~ FEITO
3. ~~Detectar automaticamente tipo de item~~ FEITO
4. Adicionar historico de precos na resposta (opcional)
5. Testes para novos modulos (aumentar cobertura para 70%)

---

**Data:** 30/01/2026 (atualizado)
**Bot rodando:** Sim (em background)
**Ultima alteracao:** Implementado suporte a itens nao-equipamentos
