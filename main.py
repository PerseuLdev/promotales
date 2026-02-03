"""
PromoTales Bot - Ponto de entrada principal
Bot do Telegram para buscar preços de itens no Ragnatales

Utiliza DrissionPage para web scraping com bypass de Cloudflare.
"""

import sys
from src.bot.telegram_bot import TelegramBot
from src.utils.logger import get_logger

logger = get_logger(__name__)


def main():
    """Função principal que inicia o bot"""
    try:
        logger.info("=" * 50)
        logger.info("Iniciando PromoTales Bot")
        logger.info("Usando DrissionPage para scraping")
        logger.info("=" * 50)

        bot = TelegramBot()
        bot.run()

    except KeyboardInterrupt:
        logger.info("Bot encerrado pelo usuário")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Erro fatal ao iniciar o bot: {str(e)}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
