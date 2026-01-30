"""
Pytest configuration and shared fixtures for PromoTales Bot tests.
"""

import os
import sys
from unittest.mock import MagicMock, Mock
import pytest

# Add src to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))


# ============================================================================
# Environment and Configuration Fixtures
# ============================================================================


@pytest.fixture(scope="session")
def test_env_vars():
    """Set up test environment variables."""
    os.environ["TELEGRAM_BOT_TOKEN"] = "123456789:ABCdefGHIjklMNOpqrsTUVwxyz"
    os.environ["ENVIRONMENT"] = "test"
    return os.environ


@pytest.fixture
def mock_settings():
    """Mock settings configuration."""
    from config.settings import Settings

    settings = Settings()
    settings.BOT_TOKEN = "123456789:ABCdefGHIjklMNOpqrsTUVwxyz"
    settings.ENVIRONMENT = "test"
    settings.TIMEOUT = 10
    settings.MAX_RETRIES = 3
    return settings


# ============================================================================
# Telegram Bot Fixtures
# ============================================================================


@pytest.fixture
def mock_telegram_bot():
    """Create a mocked Telegram Bot instance."""
    from telegram import Bot

    bot = Mock(spec=Bot)
    bot.token = "123456789:ABCdefGHIjklMNOpqrsTUVwxyz"
    bot.username = "PromoTalesBot"
    return bot


@pytest.fixture
def mock_update():
    """Create a mocked Telegram Update object."""
    from telegram import Update, Message, Chat, User

    update = Mock(spec=Update)
    update.update_id = 12345

    # Mock user
    user = Mock(spec=User)
    user.id = 123456
    user.first_name = "Test"
    user.last_name = "User"
    user.username = "testuser"
    user.is_bot = False

    # Mock chat
    chat = Mock(spec=Chat)
    chat.id = 123456
    chat.type = "private"
    chat.first_name = "Test"
    chat.last_name = "User"
    chat.username = "testuser"

    # Mock message
    message = Mock(spec=Message)
    message.message_id = 1
    message.date = None
    message.chat = chat
    message.from_user = user
    message.text = ""
    message.reply_text = MagicMock(return_value=message)

    update.message = message
    update.effective_chat = chat
    update.effective_user = user

    return update


@pytest.fixture
def mock_context():
    """Create a mocked Telegram CallbackContext."""
    from telegram.ext import CallbackContext

    context = Mock(spec=CallbackContext)
    context.bot = Mock()
    context.user_data = {}
    context.chat_data = {}
    context.bot_data = {}
    return context


# ============================================================================
# Web Scraper Fixtures
# ============================================================================


@pytest.fixture
def mock_webdriver():
    """Create a mocked Selenium WebDriver."""
    from selenium.webdriver import Chrome

    driver = Mock(spec=Chrome)
    driver.get = MagicMock()
    driver.quit = MagicMock()
    driver.close = MagicMock()
    driver.find_element = MagicMock()
    driver.find_elements = MagicMock(return_value=[])
    driver.page_source = "<html></html>"
    driver.current_url = "https://ragnatales.com.br"

    return driver


@pytest.fixture
def mock_scraper_response():
    """Mock successful scraper response data."""
    return {
        "item_name": "Elmo",
        "lowest_price": 500000,
        "average_price": 750000,
        "shop_location": "prontera 150 200",
        "total_shops": 5,
        "timestamp": "2026-01-24 12:00:00",
    }


@pytest.fixture
def sample_item_data():
    """Sample item data for testing."""
    return [
        {
            "name": "Elmo",
            "price": 500000,
            "location": "prontera 150 200",
            "seller": "TestSeller1",
        },
        {
            "name": "Elmo",
            "price": 750000,
            "location": "prontera 200 150",
            "seller": "TestSeller2",
        },
        {
            "name": "Elmo",
            "price": 600000,
            "location": "payon 100 100",
            "seller": "TestSeller3",
        },
    ]


# ============================================================================
# Rate Limiter Fixtures
# ============================================================================


@pytest.fixture
def mock_rate_limiter():
    """Create a mocked RateLimiter."""
    from utils.rate_limiter import RateLimiter

    limiter = Mock(spec=RateLimiter)
    limiter.is_allowed = MagicMock(return_value=True)
    limiter.get_remaining = MagicMock(return_value=5)
    limiter.reset = MagicMock()
    return limiter


# ============================================================================
# Validator Fixtures
# ============================================================================


@pytest.fixture
def valid_item_names():
    """List of valid item names for testing."""
    return ["Elmo", "Espada", "Poção Vermelha", "Anel de Prata", "Carta Poring"]


@pytest.fixture
def invalid_item_names():
    """List of invalid item names for testing."""
    return ["", "  ", "a", "ab", None]


# ============================================================================
# Pytest Markers
# ============================================================================


def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line("markers", "unit: Mark test as a unit test")
    config.addinivalue_line("markers", "integration: Mark test as an integration test")
    config.addinivalue_line("markers", "slow: Mark test as slow running")
    config.addinivalue_line("markers", "selenium: Mark test as requiring Selenium WebDriver")
    config.addinivalue_line(
        "markers", "requires_bot_token: Mark test as requiring TELEGRAM_BOT_TOKEN"
    )


# ============================================================================
# Cleanup Fixtures
# ============================================================================


@pytest.fixture(autouse=True)
def cleanup_after_test():
    """Cleanup after each test."""
    yield
    # Add cleanup logic here if needed
    pass


@pytest.fixture(scope="session", autouse=True)
def cleanup_session():
    """Cleanup after test session."""
    yield
    # Final cleanup after all tests
    pass
