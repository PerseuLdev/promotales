# PromoTales Bot

Bot do Telegram para buscar preços de itens no market do Ragnatales.

## Descrição

O PromoTales Bot é um assistente automatizado que ajuda jogadores do Ragnatales a encontrar os melhores preços de itens no market do jogo. Ele utiliza **DrissionPage** para web scraping com bypass de Cloudflare.

## Funcionalidades

- 🔍 Busca de itens por nome (equipamentos, cartas, consumíveis)
- 💰 Encontra o menor preço disponível
- 📊 Média de preços dos últimos 45 dias
- 📈 Volume de vendas dos últimos 45 dias
- 📅 Histórico de preços (últimos 7 dias)
- 🎴 Detalhes de cartas equipadas
- ✨ Bônus aleatórios dos equipamentos
- ⚡ Respostas rápidas via Telegram

## Informações Capturadas

| Dado | Descrição |
|------|-----------|
| Nome do item | Nome completo com slots |
| Refinamento | Nível de refino (+0 a +20) |
| Preço | Valor em zenys |
| Vendedor | Nome da loja |
| Quantidade | Unidades disponíveis |
| Cartas | Lista de cartas equipadas |
| Bônus Aleatórios | Encantamentos do item |
| Preço Médio (45d) | Média de preço do mercado |
| Volume (45d) | Total de vendas no período |
| Histórico | Min/Méd/Máx por dia |

## Requisitos

- Python 3.8+
- Google Chrome instalado
- Token do Bot do Telegram

## Instalação

1. Clone o repositório:
```bash
git clone https://github.com/PerseuLdev/promotales.git
cd promotales
```

2. Instale as dependências:
```bash
pip install -r requirements.txt
```

3. Configure as variáveis de ambiente:
```bash
# Crie um arquivo .env na raiz do projeto
BOT_TOKEN=seu_token_do_telegram_aqui
```

## Uso

Execute o bot:
```bash
python main.py
```

No Telegram:
1. Inicie uma conversa com o bot
2. Digite `/start` para começar
3. Envie o nome do item que deseja buscar

### Exemplos de Busca

- `folha afiada` - Item consumível
- `Alma da Feiticeira Celia` - Carta
- `Cajado Corrompido da Kathryne` - Equipamento com refino

## Estrutura do Projeto

```
PromoTales/
├── src/
│   ├── bot/              # Bot do Telegram
│   │   └── telegram_bot.py
│   ├── scraper/          # Web scraping com DrissionPage
│   │   └── ragnatales_scraper.py
│   ├── models/           # Modelos de dados
│   │   ├── item_offer.py
│   │   └── price_history.py
│   ├── utils/            # Utilitários
│   │   ├── browser_setup.py  # Configuração do DrissionPage
│   │   ├── logger.py
│   │   └── validators.py
│   ├── config/           # Configurações
│   │   └── settings.py
│   └── exceptions.py     # Exceções customizadas
├── tests/                # Testes automatizados
├── docs/                 # Documentação
├── main.py               # Ponto de entrada
├── requirements.txt      # Dependências
└── .env                  # Variáveis de ambiente (não versionado)
```

## Tecnologias

- **python-telegram-bot** - Interface com Telegram
- **DrissionPage** - Automação web com bypass de Cloudflare
- **python-dotenv** - Gerenciamento de variáveis de ambiente

## Configuração por Ambiente

### Local (Desenvolvimento)
- Chrome com interface gráfica
- Necessário para passar verificação Cloudflare
- Chrome path: `C:\Program Files\Google\Chrome\Application\chrome.exe`

### Cloud (Render)
- Modo headless (pode ter limitações com Cloudflare)
- Chrome path: `/usr/bin/google-chrome`
- Detectado automaticamente via variável `RENDER`

## Limitações

- **Modo Headless**: Cloudflare pode bloquear requisições em modo headless
- **Rate Limiting**: Respeite os limites do site para evitar bloqueios

## Roadmap

- [x] Estrutura de diretórios
- [x] Migração Selenium → DrissionPage
- [x] Captura de cartas e bônus aleatórios
- [x] Histórico de preços
- [ ] Cache de resultados
- [ ] Notificações de preços
- [ ] Busca em abas paralelas

## Contribuindo

1. Fork o projeto
2. Crie uma branch (`git checkout -b feature/MinhaFeature`)
3. Commit suas mudanças (`git commit -m 'Add: MinhaFeature'`)
4. Push para a branch (`git push origin feature/MinhaFeature`)
5. Abra um Pull Request

## Licença

Este projeto é de código aberto e está disponível para uso educacional.

## Contato

Para dúvidas ou sugestões, abra uma issue no GitHub.
