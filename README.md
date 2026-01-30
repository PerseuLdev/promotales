# PromoTales Bot

Bot do Telegram para buscar preços de itens no market do Ragnatales.

## Descrição

O PromoTales Bot é um assistente automatizado que ajuda jogadores do Ragnatales a encontrar os melhores preços de itens no market do jogo. Ele utiliza web scraping para coletar informações em tempo real do site oficial.

## Funcionalidades

- 🔍 Busca de itens por nome
- 💰 Encontra o menor preço disponível
- 📍 Localização exata da loja (@market X/Y)
- 📊 Média de preços do mercado
- ⚡ Respostas rápidas via Telegram

## Requisitos

- Python 3.8+
- Google Chrome instalado
- ChromeDriver (instalado automaticamente)
- Token do Bot do Telegram

## Instalação

1. Clone o repositório:
```bash
git clone <url-do-repositorio>
cd PromoTales
```

2. Instale as dependências:
```bash
pip install -r requirements.txt
```

3. Configure as variáveis de ambiente:
Crie um arquivo `.env` na raiz do projeto:
```env
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

## Estrutura do Projeto

```
PromoTales/
├── src/
│   ├── bot/          # Módulos do bot do Telegram
│   ├── scraper/      # Módulos de web scraping
│   └── utils/        # Utilitários gerais
├── tests/            # Testes automatizados
├── docs/             # Documentação adicional
├── config/           # Arquivos de configuração
├── main.py           # Arquivo principal
├── requirements.txt  # Dependências do projeto
└── .env             # Variáveis de ambiente (não versionado)
```

## Configuração para Deploy

### Render (Cloud)

O bot detecta automaticamente se está rodando no Render e ajusta as configurações:
- Modo headless
- ChromeDriver auto-instalado
- Configurações otimizadas para cloud

### Local (Desenvolvimento)

Para desenvolvimento local, certifique-se de:
- Ter o Google Chrome instalado em `C:\Program Files\Google\Chrome\Application\chrome.exe`
- Ter o `chromedriver.exe` na pasta raiz ou no PATH

## Tecnologias

- **python-telegram-bot** - Interface com Telegram
- **Selenium** - Automação web
- **selenium-wire** - Interceptação de requisições
- **python-dotenv** - Gerenciamento de variáveis de ambiente
- **chromedriver-autoinstaller** - Instalação automática do ChromeDriver

## Roadmap

### Milestone 1: Estruturação e Organização ✅
- [x] Estrutura de diretórios
- [x] Documentação inicial
- [ ] Refatoração em módulos
- [ ] Testes básicos

### Milestone 2: Melhorias e Features
- [ ] Cache de resultados
- [ ] Suporte a múltiplos itens
- [ ] Histórico de preços
- [ ] Notificações de preços

### Milestone 3: Otimizações
- [ ] Performance de scraping
- [ ] Rate limiting
- [ ] Logs estruturados
- [ ] Monitoramento

## Contribuindo

Contribuições são bem-vindas! Por favor:
1. Faça um fork do projeto
2. Crie uma branch para sua feature (`git checkout -b feature/MinhaFeature`)
3. Commit suas mudanças (`git commit -m 'Add: MinhaFeature'`)
4. Push para a branch (`git push origin feature/MinhaFeature`)
5. Abra um Pull Request

## Licença

Este projeto é de código aberto e está disponível para uso educacional.

## Contato

Para dúvidas ou sugestões, abra uma issue no GitHub.
