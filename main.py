"""
PromoTales Bot - Ponto de entrada principal
"""

from src.bot import TelegramBot
from src.utils.logger import get_logger

logger = get_logger(__name__)


def main():
    """Função principal que inicia o bot"""
    try:
        logger.info("Iniciando PromoTales Bot...")
        bot = TelegramBot()
        bot.run()
    except KeyboardInterrupt:
        logger.info("Bot encerrado pelo usuário")
    except Exception as e:
        logger.error(f"Erro fatal ao iniciar o bot: {str(e)}", exc_info=True)
        raise


if __name__ == "__main__":
    main()
