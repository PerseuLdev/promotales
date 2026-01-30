"""
Extended tests for RagnatalesScraper to improve coverage.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from selenium.common.exceptions import NoSuchElementException, TimeoutException

from src.scraper.ragnatales_scraper import RagnatalesScraper
from src.exceptions import (
    ItemNotFoundException,
    ScraperException,
    ChromeDriverException,
    PageLoadException,
)


class TestRagnatalesScraperExtended:
    """Extended tests for RagnatalesScraper."""
    
    def test_scraper_init(self):
        """Test scraper initialization."""
        scraper = RagnatalesScraper()
        assert scraper.driver is None
    
    def test_start_driver_success(self):
        """Test starting driver successfully."""
        scraper = RagnatalesScraper()
        
        with patch("src.scraper.ragnatales_scraper.setup_chrome_driver") as mock_setup:
            mock_driver = Mock()
            mock_setup.return_value = mock_driver
            
            scraper._start_driver()
            
            assert scraper.driver is not None
            assert scraper.driver == mock_driver
            mock_setup.assert_called_once()
    
    def test_start_driver_failure(self):
        """Test starting driver with error."""
        scraper = RagnatalesScraper()
        
        with patch("src.scraper.ragnatales_scraper.setup_chrome_driver") as mock_setup:
            mock_setup.side_effect = Exception("Driver error")
            
            with pytest.raises(ChromeDriverException):
                scraper._start_driver()
    
    def test_stop_driver_success(self):
        """Test stopping driver successfully."""
        scraper = RagnatalesScraper()
        mock_driver = Mock()
        scraper.driver = mock_driver
        
        scraper._stop_driver()
        
        mock_driver.quit.assert_called_once()
        assert scraper.driver is None
    
    def test_stop_driver_with_error(self):
        """Test stopping driver with error."""
        scraper = RagnatalesScraper()
        scraper.driver = Mock()
        scraper.driver.quit.side_effect = Exception("Quit error")
        
        # Should not raise exception
        scraper._stop_driver()
        
        # Driver should still be set to None
        assert scraper.driver is None
    
    def test_stop_driver_when_none(self):
        """Test stopping driver when it's None."""
        scraper = RagnatalesScraper()
        scraper.driver = None
        
        # Should not raise exception
        scraper._stop_driver()
        
        assert scraper.driver is None
    
    def test_search_item_found(self):
        """Test searching for an item that exists."""
        scraper = RagnatalesScraper()
        mock_driver = Mock()
        scraper.driver = mock_driver

        # Mock find_element calls
        mock_search_field = Mock()
        mock_item_link = Mock()

        mock_driver.find_element.side_effect = [mock_search_field, mock_item_link]

        with patch("src.scraper.ragnatales_scraper.time.sleep"):
            result = scraper._search_item("Elmo")

        assert result is True
        mock_search_field.send_keys.assert_called()
        # Now uses execute_script for click, so verify execute_script was called
        assert mock_driver.execute_script.call_count >= 2  # click on search field + click on item link
    
    def test_search_item_not_found(self):
        """Test searching for an item that doesn't exist."""
        scraper = RagnatalesScraper()
        mock_driver = Mock()
        scraper.driver = mock_driver
        
        # Mock NoSuchElementException
        mock_driver.find_element.side_effect = NoSuchElementException("Not found")
        
        with patch("src.scraper.ragnatales_scraper.time.sleep"):
            result = scraper._search_item("NonExistentItem")
        
        assert result is False
    
    def test_search_item_timeout(self):
        """Test searching with timeout error."""
        scraper = RagnatalesScraper()
        mock_driver = Mock()
        scraper.driver = mock_driver
        
        mock_driver.find_element.side_effect = TimeoutException("Timeout")
        
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



