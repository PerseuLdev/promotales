"""Testes para o módulo de scraping"""

import unittest
import re
from unittest.mock import Mock, patch, MagicMock
from src.scraper.ragnatales_scraper import RagnatalesScraper


class TestRagnatalesScraper(unittest.TestCase):
    """Testes para a classe RagnatalesScraper"""
    
    def setUp(self):
        """Configuração antes de cada teste"""
        self.scraper = RagnatalesScraper()
    
    def test_scraper_initialization(self):
        """Testa se o scraper é inicializado corretamente"""
        self.assertIsNotNone(self.scraper)
        self.assertIsNone(self.scraper.driver)
    
    def test_price_parsing_format(self):
        """Testa o formato de parsing de preços"""
        # Testa padrões comuns de preços
        test_prices = [
            ("1.000", 1000.0),
            ("10.000", 10000.0),
            ("100.000", 100000.0),
            ("1.234.567", 1234567.0),
        ]
        
        for price_str, expected in test_prices:
            # Remove pontos e converte
            cleaned = price_str.replace(".", "").replace(",", ".")
            result = float(cleaned)
            self.assertEqual(result, expected)
    
    def test_location_pattern_matching(self):
        """Testa o padrão regex para localização"""
        pattern = r"@market (\d+)/(\d+)"
        
        test_cases = [
            ("@market 123/456", True),
            ("@market 1/1", True),
            ("@market 999/999", True),
            ("market 123/456", False),
            ("@market abc/def", False),
        ]
        
        for text, should_match in test_cases:
            match = re.search(pattern, text)
            if should_match:
                self.assertIsNotNone(match)
            else:
                self.assertIsNone(match)
    
    def test_context_manager(self):
        """Testa se o context manager funciona corretamente"""
        with patch('src.scraper.ragnatales_scraper.setup_chrome_driver') as mock_driver:
            mock_driver.return_value = MagicMock()
            
            with self.scraper as scraper:
                self.assertIsNotNone(scraper.driver)
            
            # Verifica se o driver foi finalizado
            self.assertIsNone(self.scraper.driver)


class TestScraperHelpers(unittest.TestCase):
    """Testes para funções auxiliares do scraper"""
    
    def test_price_formatting(self):
        """Testa a formatação de preços"""
        test_values = [
            (1000, "1.000"),
            (10000, "10.000"),
            (100000, "100.000"),
            (1234567, "1.234.567"),
        ]
        
        for value, expected in test_values:
            result = f"{int(value):,}".replace(",", ".")
            self.assertEqual(result, expected)


if __name__ == '__main__':
    unittest.main()
