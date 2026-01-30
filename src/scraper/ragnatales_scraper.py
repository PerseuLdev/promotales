"""Scraper para o site Ragnatales"""

import re
import time
from typing import Optional, List
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import NoSuchElementException, TimeoutException

from ..config.settings import Settings
from ..utils.chrome_setup import setup_chrome_driver
from ..utils.logger import get_logger
from ..models.item_offer import ItemOffer, ItemSearchResult
from ..exceptions import (
    ItemNotFoundException,
    ScraperException,
    ChromeDriverException,
    PageLoadException
)

logger = get_logger(__name__)


class RagnatalesScraper:
    """Classe para scraping de informacoes do Ragnatales"""

    def __init__(self) -> None:
        """Inicializa o scraper"""
        self.driver: Optional[WebDriver] = None

    def _start_driver(self) -> None:
        """
        Inicia o ChromeDriver se nao estiver iniciado

        Raises:
            ChromeDriverException: Se houver erro ao iniciar o driver
        """
        if self.driver is None:
            try:
                self.driver = setup_chrome_driver()
                logger.info("ChromeDriver iniciado com sucesso")
            except Exception as e:
                logger.error(f"Erro ao iniciar ChromeDriver: {str(e)}")
                raise ChromeDriverException(f"Falha ao iniciar ChromeDriver: {str(e)}")

    def _stop_driver(self) -> None:
        """Para o ChromeDriver se estiver rodando"""
        if self.driver is not None:
            try:
                self.driver.quit()
                logger.info("ChromeDriver finalizado com sucesso")
            except Exception as e:
                logger.error(f"Erro ao finalizar ChromeDriver: {str(e)}")
            finally:
                self.driver = None

    def _search_item(self, item_name: str) -> bool:
        """
        Busca um item no site

        Args:
            item_name: Nome do item a buscar

        Returns:
            bool: True se encontrou o item, False caso contrario
        """
        try:
            # Navega para a pagina de itens
            logger.debug(f"Navegando para: {Settings.RAGNATALES_URL}")
            self.driver.get(Settings.RAGNATALES_URL)
            time.sleep(Settings.PAGE_LOAD_TIMEOUT)

            # Busca pelo item
            search_field = self.driver.find_element(
                By.CSS_SELECTOR,
                "input[placeholder='Filtrar por nome']"
            )
            self.driver.execute_script('arguments[0].click();', search_field)
            search_field.send_keys(item_name, Keys.ENTER)
            logger.debug(f"Termo de busca enviado: '{item_name}'")
            time.sleep(Settings.SEARCH_TIMEOUT)

            # Clica no primeiro item encontrado
            item_link = self.driver.find_element(
                By.XPATH,
                '//a[starts-with(@href, "/db/items/")]'
            )
            self.driver.execute_script('arguments[0].click();', item_link)
            time.sleep(Settings.CLICK_TIMEOUT)

            logger.info(f"Item '{item_name}' encontrado e selecionado")
            return True

        except NoSuchElementException:
            logger.warning(f"Item '{item_name}' nao encontrado no site")
            return False
        except TimeoutException:
            logger.error(f"Timeout ao buscar item '{item_name}'")
            raise PageLoadException(Settings.RAGNATALES_URL, Settings.PAGE_LOAD_TIMEOUT)
        except Exception as e:
            logger.error(f"Erro inesperado ao buscar item '{item_name}': {str(e)}")
            raise ScraperException(f"Erro ao buscar item: {str(e)}", e)

    def _get_average_price(self) -> Optional[str]:
        """
        Obtem o preco medio do item

        Returns:
            str: Preco medio ou None se nao encontrado
        """
        try:
            media_element = self.driver.find_element(
                By.XPATH,
                '//div[contains(text(), "A Média de preço deste item é de")]'
            )
            media_texto = media_element.text
            media_price_match = re.search(r"[\d.]+", media_texto)

            if media_price_match:
                price = media_price_match.group(0)
                logger.info(f"Preco medio encontrado: {price}")
                return price

        except NoSuchElementException:
            logger.info("Preco medio nao disponivel")
        except Exception as e:
            logger.error(f"Erro ao obter preco medio: {str(e)}")

        return None

    def _get_sales_volume(self) -> Optional[str]:
        """
        Obtem o volume de vendas dos ultimos 45 dias

        Returns:
            str: Volume de vendas ou None se nao encontrado
        """
        try:
            vendas_element = self.driver.find_element(
                By.XPATH,
                '//div[contains(text(), "Este item foi vendido")]'
            )
            vendas_texto = vendas_element.text
            # Extrai o numero de vendas: "Este item foi vendido 125.291 vezes"
            vendas_match = re.search(r"vendido\s+([\d.]+)\s+vezes", vendas_texto)

            if vendas_match:
                volume = vendas_match.group(1)
                logger.info(f"Volume de vendas encontrado: {volume}")
                return volume

        except NoSuchElementException:
            logger.info("Volume de vendas nao disponivel")
        except Exception as e:
            logger.error(f"Erro ao obter volume de vendas: {str(e)}")

        return None

    def _get_all_offers(self) -> List[ItemOffer]:
        """
        Obtem todas as ofertas das lojas

        Returns:
            Lista de ItemOffer
        """
        ofertas = []

        try:
            # Clica no botao de lojas
            shops_button = self.driver.find_element(
                By.XPATH,
                '//button[contains(., "lojas")]'
            )
            self.driver.execute_script(
                "arguments[0].scrollIntoView({block: 'center'});",
                shops_button
            )
            time.sleep(1)
            self.driver.execute_script('arguments[0].click();', shops_button)
            time.sleep(Settings.SHOPS_TIMEOUT)

            # Busca containers das lojas
            lojas_elements = self.driver.find_elements(
                By.CSS_SELECTOR,
                ".rounded-sm.bg-white.text-black.px-4.py-2.text-base"
            )

            logger.info(f"Encontrados {len(lojas_elements)} containers de lojas")

            for loja_el in lojas_elements:
                try:
                    texto = loja_el.text
                    # Ignora a descricao do item (primeiro container)
                    if "Classe:" in texto or "Defesa:" in texto:
                        continue

                    # Divide em ofertas individuais (pode ter varias no mesmo container)
                    # Cada oferta comeca com nome do item ou +X
                    ofertas_texto = self._split_ofertas(texto)

                    for oferta_texto in ofertas_texto:
                        oferta = ItemOffer.from_text(oferta_texto)
                        if oferta:
                            ofertas.append(oferta)
                            logger.debug(f"Oferta parseada: {oferta.nome_completo()} - {oferta.preco_formatado()}z")

                except Exception as e:
                    logger.debug(f"Erro ao processar loja: {str(e)}")
                    continue

            logger.info(f"Total de ofertas parseadas: {len(ofertas)}")

        except NoSuchElementException:
            logger.warning("Botao de lojas nao encontrado - item sem ofertas no market")
        except Exception as e:
            logger.error(f"Erro ao obter ofertas: {str(e)}")

        return ofertas

    def _split_ofertas(self, texto: str) -> List[str]:
        """
        Divide o texto de um container em ofertas individuais

        Args:
            texto: Texto do container

        Returns:
            Lista de textos de ofertas individuais
        """
        linhas = texto.split('\n')
        ofertas = []
        oferta_atual = []
        dentro_cartas = False

        for linha in linhas:
            linha_strip = linha.strip()

            # Marca quando entra/sai da secao de cartas
            if linha_strip == "Cartas Equipadas:":
                dentro_cartas = True
                if oferta_atual:
                    oferta_atual.append(linha_strip)
                continue
            elif "Bônus Aleatórios:" in linha_strip or linha_strip.startswith("Vendedor:"):
                dentro_cartas = False

            # Detecta inicio de nova oferta
            # Equipamento: +9NomeItem [1] (id: xxx) ou NomeItem [1] (id: xxx)
            # Item simples: NomeItem (id: xxx) - sem [slots]
            is_nova_oferta = False

            # Nao detecta nova oferta se estiver dentro da secao de cartas
            if not dentro_cartas:
                # Padrao equipamento: tem [slots] e (id:)
                if re.match(r'^(\+\d+)?[A-Z].*\[\d\]\s*\(id:', linha_strip):
                    is_nova_oferta = True
                # Padrao item simples: nao tem [slots], mas tem (id:) e NAO comeca com "Carta"
                elif re.match(r'^[A-Z].*\(id:\s*\d+\)', linha_strip) and '[' not in linha_strip:
                    # Ignora se parece ser uma carta
                    if not linha_strip.startswith("Carta "):
                        is_nova_oferta = True

            if is_nova_oferta:
                if oferta_atual:
                    ofertas.append('\n'.join(oferta_atual))
                oferta_atual = [linha_strip]
                dentro_cartas = False
            elif oferta_atual:
                oferta_atual.append(linha_strip)

        # Adiciona ultima oferta
        if oferta_atual:
            ofertas.append('\n'.join(oferta_atual))

        return ofertas

    def search_item(self, item_name: str) -> ItemSearchResult:
        """
        Busca completa de um item com todas as ofertas

        Args:
            item_name: Nome do item a buscar

        Returns:
            ItemSearchResult com todas as ofertas
        """
        is_context_manager = self.driver is not None

        try:
            logger.info(f"Iniciando busca completa por '{item_name}'")
            self._start_driver()

            # Busca o item
            if not self._search_item(item_name):
                raise ItemNotFoundException(item_name)

            # Obtem preco medio
            preco_medio = self._get_average_price()

            # Obtem volume de vendas
            volume_vendas = self._get_sales_volume()

            # Obtem todas as ofertas
            ofertas = self._get_all_offers()

            if not ofertas:
                raise ItemNotFoundException(item_name)

            # Usa o nome real do item (da primeira oferta) em vez do termo buscado
            nome_real = ofertas[0].nome if ofertas else item_name

            result = ItemSearchResult(
                item_nome=nome_real,
                ofertas=ofertas,
                preco_medio=preco_medio,
                volume_vendas=volume_vendas
            )

            logger.info(f"Busca concluida: {len(ofertas)} ofertas para '{item_name}'")
            return result

        except ItemNotFoundException:
            raise

        except (ChromeDriverException, PageLoadException, ScraperException):
            raise

        except Exception as e:
            logger.error(f"Erro nao tratado ao buscar '{item_name}': {str(e)}", exc_info=True)
            raise ScraperException(f"Erro inesperado ao buscar item: {str(e)}", e)

        finally:
            if not is_context_manager:
                self._stop_driver()

    def get_item_info(self, item_name: str) -> str:
        """
        Busca informacoes do item (compatibilidade com versao antiga)

        Args:
            item_name: Nome do item a buscar

        Returns:
            str: Mensagem formatada com as informacoes do item
        """
        result = self.search_item(item_name)
        mais_barato = result.mais_barato()

        if mais_barato:
            response = mais_barato.to_message(mostrar_detalhes=True)
            if result.preco_medio:
                response += f"\n📊 Media 45d: {result.preco_medio} zenys"
            if result.volume_vendas:
                response += f"\n📈 Vendas 45d: {result.volume_vendas}"
            return response

        raise ItemNotFoundException(item_name)

    def __enter__(self):
        """Context manager - entrada"""
        self._start_driver()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager - saida"""
        self._stop_driver()
