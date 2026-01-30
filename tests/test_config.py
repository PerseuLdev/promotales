"""Testes para o módulo de configuração"""

import unittest
import os
from src.config.settings import Settings


class TestSettings(unittest.TestCase):
    """Testes para a classe Settings"""
    
    def test_ragnatales_url_exists(self):
        """Testa se a URL do Ragnatales está configurada"""
        self.assertIsNotNone(Settings.RAGNATALES_URL)
        self.assertTrue(Settings.RAGNATALES_URL.startswith("https://"))
    
    def test_timeouts_are_positive(self):
        """Testa se os timeouts são valores positivos"""
        self.assertGreater(Settings.PAGE_LOAD_TIMEOUT, 0)
        self.assertGreater(Settings.SEARCH_TIMEOUT, 0)
        self.assertGreater(Settings.CLICK_TIMEOUT, 0)
        self.assertGreater(Settings.SHOPS_TIMEOUT, 0)
    
    def test_chrome_paths_exist(self):
        """Testa se os caminhos do Chrome estão configurados"""
        self.assertIsNotNone(Settings.CHROME_BINARY_LOCAL)
        self.assertIsNotNone(Settings.CHROME_BINARY_RENDER)
    
    def test_is_render_is_boolean(self):
        """Testa se IS_RENDER é um booleano"""
        self.assertIsInstance(Settings.IS_RENDER, bool)


if __name__ == '__main__':
    unittest.main()
