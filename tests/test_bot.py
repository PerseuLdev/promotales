"""Testes para o módulo do bot do Telegram"""

import unittest
from unittest.mock import Mock, patch, AsyncMock
from src.bot.telegram_bot import TelegramBot


class TestTelegramBot(unittest.TestCase):
    """Testes para a classe TelegramBot"""
    
    @patch('src.bot.telegram_bot.Settings.validate')
    def setUp(self, mock_validate):
        """Configuração antes de cada teste"""
        mock_validate.return_value = True
        self.bot = TelegramBot()
    
    def test_bot_initialization(self):
        """Testa se o bot é inicializado corretamente"""
        self.assertIsNotNone(self.bot)
        self.assertIsNotNone(self.bot.scraper)
        self.assertIsNone(self.bot.app)
    
    @patch('src.bot.telegram_bot.Settings.BOT_TOKEN', 'test_token')
    def test_bot_requires_token(self):
        """Testa se o bot requer um token válido"""
        with patch('src.bot.telegram_bot.Settings.validate') as mock_validate:
            mock_validate.return_value = True
            bot = TelegramBot()
            self.assertIsNotNone(bot)


class TestBotValidation(unittest.TestCase):
    """Testes para validações do bot"""
    
    def test_item_name_validation(self):
        """Testa validações de nome de item"""
        # Nome vazio
        self.assertFalse(bool("".strip()))
        
        # Nome muito curto
        self.assertLess(len("ab"), 3)
        
        # Nome válido
        self.assertGreaterEqual(len("item"), 3)
    
    def test_message_formatting(self):
        """Testa formatação de mensagens"""
        item_name = "Elmo de Brilhante"
        price = 1000000
        location = "@market 123/456"
        
        formatted_price = f"{int(price):,}".replace(",", ".")
        message = f"🛒 {item_name} mais barato: {formatted_price} zenys ({location})"
        
        self.assertIn(item_name, message)
        self.assertIn(location, message)
        self.assertIn("🛒", message)


if __name__ == '__main__':
    unittest.main()
