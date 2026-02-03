"""
Extended tests for RagnatalesScraper to improve coverage.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock

from DrissionPage.errors import ElementNotFoundError

from src.scraper.ragnatales_scraper import RagnatalesScraper
from src.exceptions import (
    ItemNotFoundException,
    ScraperException,
    BrowserException,
    PageLoadException,
)


class TestRagnatalesScraperExtended:
    """Extended tests for RagnatalesScraper."""

    def test_scraper_init(self):
        """Test scraper initialization."""
        scraper = RagnatalesScraper()
        assert scraper.page is None

    def test_start_driver_success(self):
        """Test starting driver successfully."""
        scraper = RagnatalesScraper()

        with patch("src.scraper.ragnatales_scraper.setup_browser") as mock_setup:
            mock_page = Mock()
            mock_setup.return_value = mock_page

            scraper._start_driver()

            assert scraper.page is not None
            assert scraper.page == mock_page
            mock_setup.assert_called_once()

    def test_start_driver_failure(self):
        """Test starting driver with error."""
        scraper = RagnatalesScraper()

        with patch("src.scraper.ragnatales_scraper.setup_browser") as mock_setup:
            mock_setup.side_effect = Exception("Browser error")

            with pytest.raises(BrowserException):
                scraper._start_driver()

    def test_stop_driver_success(self):
        """Test stopping driver successfully."""
        scraper = RagnatalesScraper()
        mock_page = Mock()
        scraper.page = mock_page

        scraper._stop_driver()

        mock_page.quit.assert_called_once()
        assert scraper.page is None

    def test_stop_driver_with_error(self):
        """Test stopping driver with error."""
        scraper = RagnatalesScraper()
        scraper.page = Mock()
        scraper.page.quit.side_effect = Exception("Quit error")

        # Should not raise exception
        scraper._stop_driver()

        # Page should still be set to None
        assert scraper.page is None

    def test_stop_driver_when_none(self):
        """Test stopping driver when it's None."""
        scraper = RagnatalesScraper()
        scraper.page = None

        # Should not raise exception
        scraper._stop_driver()

        assert scraper.page is None

    def test_search_item_found(self):
        """Test searching for an item that exists."""
        scraper = RagnatalesScraper()
        mock_page = Mock()
        scraper.page = mock_page

        # Mock ele calls
        mock_search_field = Mock()
        mock_item_link = Mock()

        mock_page.ele.side_effect = [mock_search_field, mock_item_link]

        with patch("src.scraper.ragnatales_scraper.time.sleep"):
            result = scraper._search_item("Elmo")

        assert result is True
        mock_search_field.click.assert_called()
        mock_search_field.input.assert_called()
        mock_item_link.click.assert_called()

    def test_search_item_not_found(self):
        """Test searching for an item that doesn't exist."""
        scraper = RagnatalesScraper()
        mock_page = Mock()
        scraper.page = mock_page

        # Mock ElementNotFoundError
        mock_page.ele.side_effect = ElementNotFoundError()

        with patch("src.scraper.ragnatales_scraper.time.sleep"):
            result = scraper._search_item("NonExistentItem")

        assert result is False

    def test_search_item_timeout(self):
        """Test searching with timeout error."""
        scraper = RagnatalesScraper()
        mock_page = Mock()
        scraper.page = mock_page

        mock_page.ele.side_effect = Exception("timeout occurred")

        with patch("src.scraper.ragnatales_scraper.time.sleep"):
            with pytest.raises(PageLoadException):
                scraper._search_item("TestItem")

    def test_context_manager_enter(self):
        """Test context manager __enter__."""
        scraper = RagnatalesScraper()

        with patch.object(scraper, "_start_driver"):
            result = scraper.__enter__()

            assert result == scraper
            scraper._start_driver.assert_called_once()

    def test_context_manager_exit(self):
        """Test context manager __exit__."""
        scraper = RagnatalesScraper()

        with patch.object(scraper, "_stop_driver"):
            scraper.__exit__(None, None, None)

            scraper._stop_driver.assert_called_once()

    def test_get_item_info_not_found(self):
        """Test get_item_info when item is not found."""
        scraper = RagnatalesScraper()

        with patch.object(scraper, "_start_driver"):
            with patch.object(scraper, "_stop_driver"):
                with patch.object(scraper, "_search_item", return_value=False):
                    with pytest.raises(ItemNotFoundException):
                        scraper.get_item_info("NonExistentItem")

    def test_get_item_info_scraper_exception(self):
        """Test get_item_info with scraper exception."""
        scraper = RagnatalesScraper()

        with patch.object(scraper, "_start_driver"):
            with patch.object(scraper, "_stop_driver"):
                with patch.object(scraper, "_search_item", side_effect=Exception("Error")):
                    with pytest.raises(ScraperException):
                        scraper.get_item_info("TestItem")
