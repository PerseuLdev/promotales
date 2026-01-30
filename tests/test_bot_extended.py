"""
Extended tests for Telegram Bot to improve coverage.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from telegram import Update, Message, Chat, User
from telegram.ext import ContextTypes

from src.bot.telegram_bot import TelegramBot
from src.exceptions import (
    InvalidItemNameException,
    RateLimitExceededException,
    ItemNotFoundException,
    PromoTalesException,
)


@pytest.fixture
def bot():
    """Create a TelegramBot instance."""
    with patch("src.bot.telegram_bot.Settings.validate"):
        bot = TelegramBot()
        bot.scraper = Mock()
        return bot


@pytest.fixture
def mock_update():
    """Create a mock Update object."""
    update = Mock(spec=Update)
    
    user = Mock(spec=User)
    user.id = 12345
    user.username = "testuser"
    user.first_name = "Test"
    
    chat = Mock(spec=Chat)
    chat.id = 12345
    
    message = AsyncMock(spec=Message)
    message.text = "Test Item"
    message.reply_text = AsyncMock()
    
    update.effective_user = user
    update.message = message
    
    return update


@pytest.fixture
def mock_context():
    """Create a mock context."""
    context = Mock(spec=ContextTypes.DEFAULT_TYPE)
    context.error = None
    return context


class TestTelegramBotCommands:
    """Test command handlers."""
    
    @pytest.mark.asyncio
    async def test_start_command(self, bot, mock_update, mock_context):
        """Test /start command."""
        await bot.start_command(mock_update, mock_context)
        
        # Verify reply_text was called
        mock_update.message.reply_text.assert_called_once()
        
        # Verify welcome message content
        call_args = mock_update.message.reply_text.call_args[0][0]
        assert "Bem-vindo" in call_args
        assert "PromoTales Bot" in call_args
    
    @pytest.mark.asyncio
    async def test_help_command(self, bot, mock_update, mock_context):
        """Test /help command."""
        await bot.help_command(mock_update, mock_context)
        
        # Verify reply_text was called with Markdown
        mock_update.message.reply_text.assert_called_once()
        call_kwargs = mock_update.message.reply_text.call_args[1]
        assert call_kwargs.get("parse_mode") == "Markdown"
        
        # Verify help message content
        call_args = mock_update.message.reply_text.call_args[0][0]
        assert "Como usar" in call_args
        assert "/start" in call_args
        assert "/help" in call_args


class TestTelegramBotMessageHandling:
    """Test message handling."""
    
    @pytest.mark.asyncio
    async def test_handle_message_success(self, bot, mock_update, mock_context):
        """Test successful item search."""
        # Mock successful scraper response
        from src.models.item_offer import ItemOffer, ItemSearchResult
        mock_oferta = ItemOffer(
            nome="Elmo [1]",
            preco=500000,
            localizacao="@market 100/200",
            refinamento=0
        )
        mock_result = ItemSearchResult(
            item_nome="Elmo",
            ofertas=[mock_oferta],
            preco_medio="500.000"
        )
        bot.scraper.search_item = Mock(return_value=mock_result)

        # Mock delete for status message
        mock_update.message.reply_text.return_value.delete = AsyncMock()

        with patch("src.bot.telegram_bot.global_rate_limiter") as mock_limiter:
            mock_limiter.check_rate_limit = Mock()
            mock_limiter.get_remaining_requests = Mock(return_value=4)
            mock_limiter.max_requests = 5

            with patch("src.bot.telegram_bot.validate_item_name") as mock_validate:
                mock_validate.return_value = "Elmo"

                await bot.handle_message(mock_update, mock_context)

        # Verify scraper was called
        bot.scraper.search_item.assert_called_once_with("Elmo")
    
    @pytest.mark.asyncio
    async def test_handle_message_rate_limit_exceeded(self, bot, mock_update, mock_context):
        """Test rate limit exceeded error."""
        with patch("src.bot.telegram_bot.global_rate_limiter") as mock_limiter:
            mock_limiter.check_rate_limit = Mock(
                side_effect=RateLimitExceededException(user_id=12345, wait_time=60)
            )
            
            await bot.handle_message(mock_update, mock_context)
        
        # Verify error message was sent
        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args[0][0]
        assert "⏳" in call_args or "Rate limit" in call_args
    
    @pytest.mark.asyncio
    async def test_handle_message_invalid_item_name(self, bot, mock_update, mock_context):
        """Test invalid item name error."""
        with patch("src.bot.telegram_bot.global_rate_limiter") as mock_limiter:
            mock_limiter.check_rate_limit = Mock()
            
            with patch("src.bot.telegram_bot.validate_item_name") as mock_validate:
                mock_validate.side_effect = InvalidItemNameException(
                    item_name="ab",
                    reason="Nome muito curto"
                )
                
                await bot.handle_message(mock_update, mock_context)
        
        # Verify error message was sent
        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args[0][0]
        assert "❌" in call_args
    
    @pytest.mark.asyncio
    async def test_handle_message_item_not_found(self, bot, mock_update, mock_context):
        """Test item not found error."""
        # Mock delete for status message
        mock_update.message.reply_text.return_value.delete = AsyncMock()

        with patch("src.bot.telegram_bot.global_rate_limiter") as mock_limiter:
            mock_limiter.check_rate_limit = Mock()
            mock_limiter.get_remaining_requests = Mock(return_value=4)
            mock_limiter.max_requests = 5

            with patch("src.bot.telegram_bot.validate_item_name") as mock_validate:
                mock_validate.return_value = "NonExistentItem"

                bot.scraper.search_item = Mock(
                    side_effect=ItemNotFoundException(item_name="NonExistentItem")
                )

                await bot.handle_message(mock_update, mock_context)

        # Verify messages were sent (processing + error)
        assert mock_update.message.reply_text.call_count == 2
    
    @pytest.mark.asyncio
    async def test_handle_message_scraper_exception(self, bot, mock_update, mock_context):
        """Test ScraperException error."""
        # Mock delete for status message
        mock_update.message.reply_text.return_value.delete = AsyncMock()

        with patch("src.bot.telegram_bot.global_rate_limiter") as mock_limiter:
            mock_limiter.check_rate_limit = Mock()
            mock_limiter.get_remaining_requests = Mock(return_value=4)
            mock_limiter.max_requests = 5

            with patch("src.bot.telegram_bot.validate_item_name") as mock_validate:
                mock_validate.return_value = "TestItem"

                from src.exceptions import ScraperException
                bot.scraper.search_item = Mock(
                    side_effect=ScraperException("Erro de scraping")
                )

                await bot.handle_message(mock_update, mock_context)

        # Verify error message was sent
        assert mock_update.message.reply_text.call_count >= 1

    @pytest.mark.asyncio
    async def test_handle_message_unexpected_exception(self, bot, mock_update, mock_context):
        """Test unexpected exception handling."""
        # Mock delete for status message
        mock_update.message.reply_text.return_value.delete = AsyncMock()

        with patch("src.bot.telegram_bot.global_rate_limiter") as mock_limiter:
            mock_limiter.check_rate_limit = Mock()
            mock_limiter.get_remaining_requests = Mock(return_value=4)
            mock_limiter.max_requests = 5

            with patch("src.bot.telegram_bot.validate_item_name") as mock_validate:
                mock_validate.return_value = "TestItem"

                bot.scraper.search_item = Mock(
                    side_effect=ValueError("Unexpected error")
                )

                await bot.handle_message(mock_update, mock_context)

        # Verify error message was sent
        assert mock_update.message.reply_text.call_count >= 1


class TestTelegramBotErrorHandler:
    """Test error handler."""
    
    @pytest.mark.asyncio
    async def test_error_handler_with_update(self, bot, mock_update, mock_context):
        """Test error handler with valid update."""
        mock_context.error = Exception("Test error")
        
        await bot.error_handler(mock_update, mock_context)
        
        # Verify error message was sent
        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args[0][0]
        assert "❌" in call_args or "erro" in call_args.lower()
    
    @pytest.mark.asyncio
    async def test_error_handler_without_message(self, bot, mock_context):
        """Test error handler without message."""
        mock_update = Mock()
        mock_update.message = None
        mock_context.error = Exception("Test error")
        
        # Should not raise exception
        await bot.error_handler(mock_update, mock_context)


class TestTelegramBotSetup:
    """Test bot setup methods."""
    
    def test_setup_handlers(self, bot):
        """Test handler setup."""
        bot.app = Mock()
        bot.app.add_handler = Mock()
        bot.app.add_error_handler = Mock()

        bot.setup_handlers()

        # Verify handlers were added (start, help, callback query, message handler, error handler)
        assert bot.app.add_handler.call_count == 4  # start, help, ref_callback, message
        bot.app.add_error_handler.assert_called_once()
    
    def test_run_local_environment(self, bot):
        """Test bot run in local environment."""
        with patch("src.bot.telegram_bot.ApplicationBuilder") as mock_builder:
            mock_app_builder = Mock()
            mock_app = Mock()
            mock_app_builder.build.return_value = mock_app
            mock_builder.return_value.token.return_value = mock_app_builder
            
            with patch("src.bot.telegram_bot.Settings.BOT_TOKEN", "test_token"):
                with patch("src.bot.telegram_bot.Settings.IS_RENDER", False):
                    with patch.object(bot, "setup_handlers"):
                        bot.run()
            
            # Verify app was built and run_polling was called
            mock_app.run_polling.assert_called_once()
    
    def test_run_render_environment(self, bot):
        """Test bot run in Render environment."""
        with patch("src.bot.telegram_bot.ApplicationBuilder") as mock_builder:
            mock_app_builder = Mock()
            mock_app = Mock()
            mock_app_builder.build.return_value = mock_app
            mock_builder.return_value.token.return_value = mock_app_builder
            
            with patch("src.bot.telegram_bot.Settings.BOT_TOKEN", "test_token"):
                with patch("src.bot.telegram_bot.Settings.IS_RENDER", True):
                    with patch.object(bot, "setup_handlers"):
                        bot.run()
            
            # Verify app was built and run_polling was called
            mock_app.run_polling.assert_called_once()
