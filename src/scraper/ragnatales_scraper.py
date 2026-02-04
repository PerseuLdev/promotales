"""Scraper para o site Ragnatales usando DrissionPage"""

import re
import time
from typing import Optional, List

from DrissionPage import ChromiumPage
from DrissionPage.errors import ElementNotFoundError

from ..config.settings import Settings
from ..utils.browser_setup import setup_browser
from ..utils.logger import get_logger
from ..models.item_offer import ItemOffer, ItemSearchResult
from ..models.price_history import PriceHistory, PriceHistoryEntry
from ..exceptions import (
    ItemNotFoundException,
    ScraperException,
    BrowserException,
    PageLoadException
)

logger = get_logger(__name__)


class RagnatalesScraper:
    """Classe para scraping de informacoes do Ragnatales"""

    def __init__(self, browser: Optional[ChromiumPage] = None) -> None:
        """
        Inicializa o scraper.

        Args:
            browser: Instância externa do browser (opcional).
                     Se fornecido, o scraper reutiliza este browser
                     e NÃO o fecha ao finalizar.
        """
        self.page: Optional[ChromiumPage] = browser
        self._external_browser: bool = browser is not None

    def _start_driver(self) -> None:
        """
        Inicia o Browser se nao estiver iniciado

        Raises:
            BrowserException: Se houver erro ao iniciar o browser
        """
        if self.page is None:
            try:
                self.page = setup_browser()
                logger.info("Browser iniciado com sucesso")
            except Exception as e:
                logger.error(f"Erro ao iniciar Browser: {str(e)}")
                raise BrowserException(f"Falha ao iniciar Browser: {str(e)}")

    def _stop_driver(self) -> None:
        """Para o Browser se estiver rodando e não for externo"""
        if self.page is not None:
            if self._external_browser:
                # Não fecha browser externo, apenas limpa referência
                logger.debug("Browser externo - não será fechado pelo scraper")
                self.page = None
            else:
                try:
                    self.page.quit()
                    logger.info("Browser finalizado com sucesso")
                except Exception as e:
                    logger.error(f"Erro ao finalizar Browser: {str(e)}")
                finally:
                    self.page = None

    def _search_item(self, item_name: str) -> bool:
        """
        Busca um item no site

        Args:
            item_name: Nome do item a buscar

        Returns:
            bool: True se encontrou o item, False caso contrario
        """
        try:
            # Navega para a pagina de itens (URL limpa, sem filtros anteriores)
            clean_url = Settings.RAGNATALES_URL.split('?')[0]
            logger.debug(f"Navegando para: {clean_url}")
            self.page.get(clean_url)

            # Espera campo de busca carregar (timeout de 15s)
            search_field = self.page.ele("css:input[placeholder='Filtrar por nome']", timeout=15)
            search_field.click()
            search_field.clear()
            time.sleep(0.5)
            search_field.input(item_name + '\n')
            logger.info(f"Termo digitado no campo de busca: '{item_name}'")

            # Espera o link do item aparecer (timeout de 10s)
            item_link = self.page.ele('xpath://a[starts-with(@href, "/db/items/")]', timeout=10)
            item_link.click()

            # Espera pagina do item carregar - aguarda botao de lojas existir
            self.page.ele('xpath://button[contains(., "lojas")]', timeout=15)

            logger.info(f"Item '{item_name}' encontrado e selecionado")
            return True

        except ElementNotFoundError:
            logger.warning(f"Item '{item_name}' nao encontrado no site")
            return False
        except Exception as e:
            if "timeout" in str(e).lower():
                logger.error(f"Timeout ao buscar item '{item_name}'")
                raise PageLoadException(Settings.RAGNATALES_URL, Settings.PAGE_LOAD_TIMEOUT)
            logger.error(f"Erro inesperado ao buscar item '{item_name}': {str(e)}")
            raise ScraperException(f"Erro ao buscar item: {str(e)}", e)

    def _get_average_price(self) -> Optional[str]:
        """
        Obtem o preco medio do item

        Returns:
            str: Preco medio ou None se nao encontrado
        """
        try:
            media_element = self.page.ele(
                'xpath://div[contains(text(), "A Média de preço deste item é de")]'
            )
            media_texto = media_element.text
            media_price_match = re.search(r"[\d.]+", media_texto)

            if media_price_match:
                price = media_price_match.group(0)
                logger.info(f"Preco medio encontrado: {price}")
                return price

        except ElementNotFoundError:
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
            vendas_element = self.page.ele(
                'xpath://div[contains(text(), "Este item foi vendido")]'
            )
            vendas_texto = vendas_element.text
            # Extrai o numero de vendas: "Este item foi vendido 125.291 vezes"
            vendas_match = re.search(r"vendido\s+([\d.]+)\s+vezes", vendas_texto)

            if vendas_match:
                volume = vendas_match.group(1)
                logger.info(f"Volume de vendas encontrado: {volume}")
                return volume

        except ElementNotFoundError:
            logger.info("Volume de vendas nao disponivel")
        except Exception as e:
            logger.error(f"Erro ao obter volume de vendas: {str(e)}")

        return None

    def _get_price_history(self, item_nome: str, dias: int = 7) -> Optional[PriceHistory]:
        """
        Obtem o historico de precos do item.

        Args:
            item_nome: Nome do item
            dias: Numero de dias de historico (max 7)

        Returns:
            PriceHistory ou None se nao encontrado
        """
        try:
            # Tenta encontrar a tabela de historico
            history_rows = []

            logger.info("Buscando historico de precos...")

            # Primeiro, scrolla para a secao de estatisticas
            try:
                stats_section = self.page.ele(
                    'xpath://*[@id="app"]/div/div/div[2]/div/div[3]/div/div/div/div[5]/div[2]/div[2]',
                    timeout=3
                )
                if stats_section:
                    stats_section.scroll.to_see()
                    time.sleep(1)  # Aguarda renderizar
                    logger.info("Scroll para secao de estatisticas realizado")
            except ElementNotFoundError:
                logger.info("Secao de estatisticas nao encontrada para scroll")

            # XPath com ID (mais confiavel)
            try:
                history_container = self.page.ele(
                    'xpath://*[@id="app"]/div/div/div[2]/div/div[3]/div/div/div/div[5]/div[2]/div[2]/div/div[2]/div/div',
                    timeout=3
                )
                if history_container:
                    history_rows = history_container.eles("tag:tr")
                    logger.info(f"Encontradas {len(history_rows)} linhas via XPath com ID")
            except ElementNotFoundError:
                logger.info("XPath com ID nao encontrado, tentando alternativas...")

            # Fallback: XPath completo
            if not history_rows:
                try:
                    history_container = self.page.ele(
                        "xpath:/html/body/div/div/div/div[2]/div/div[3]/div/div/div/div[5]/div[2]/div[2]/div/div[2]/div/div"
                    )
                    if history_container:
                        history_rows = history_container.eles("tag:tr")
                        logger.info(f"Encontradas {len(history_rows)} linhas via XPath completo")
                except ElementNotFoundError:
                    logger.info("XPath completo nao encontrado")

            # Fallback: CSS selector tbody.bg-white tr
            if not history_rows:
                history_rows = self.page.eles("css:tbody.bg-white tr")
                if history_rows:
                    logger.info(f"Encontradas {len(history_rows)} linhas via CSS selector")
                else:
                    logger.info("Nenhuma linha de historico encontrada com nenhum seletor")

            if not history_rows:
                logger.info("Tabela de historico nao encontrada")
                return None

            logger.debug(f"Encontradas {len(history_rows)} linhas de historico")

            entries = []
            # Pula a primeira linha (cabecalho)
            for row in history_rows[1:dias+1]:
                try:
                    # Pega o texto completo da linha e parseia
                    row_text = row.text
                    if row_text:
                        entry = self._parse_history_row_text(row_text)
                        if entry and entry.preco_medio > 0:
                            entries.append(entry)
                            logger.debug(f"Historico parseado: {entry.data} - Med: {entry.preco_medio}")

                except Exception as e:
                    logger.debug(f"Erro ao processar linha do historico: {str(e)}")
                    continue

            if entries:
                logger.info(f"Historico encontrado: {len(entries)} entradas")
                return PriceHistory(item_nome=item_nome, entries=entries)

        except ElementNotFoundError:
            logger.info("Historico de precos nao disponivel")
        except Exception as e:
            logger.error(f"Erro ao obter historico de precos: {str(e)}")

        return None

    def _parse_history_row_text(self, texto: str) -> Optional[PriceHistoryEntry]:
        """
        Parseia o texto de uma linha do historico.

        O texto vem separado por tabs no formato:
        DATA\t\tREF\t\tCARTAS\t\tBONUS\t\tQTD\t\tMIN\t\tMED\t\tMAX\t\tTOTAL
        Exemplo:
        2 de fev. de 2026\t\t Não refinado \t\t Nenhuma carta equipada \t\t Nenhum bônus aleatório \t\t1.573\t\t4.857\t\t4.878\t\t4.900\t\t7.673.049
        """
        try:
            # Divide por tabs e limpa espacos
            colunas = [c.strip() for c in texto.split('\t') if c.strip()]
            if len(colunas) < 5:
                return None

            # Extrai data (primeira coluna)
            data_completa = colunas[0]
            data_match = re.match(r'(\d+)\s+de\s+(\w+)', data_completa)
            if data_match:
                dia = data_match.group(1)
                mes_nome = data_match.group(2).lower()
                meses = {
                    'jan': '01', 'fev': '02', 'mar': '03', 'abr': '04',
                    'mai': '05', 'jun': '06', 'jul': '07', 'ago': '08',
                    'set': '09', 'out': '10', 'nov': '11', 'dez': '12'
                }
                mes = meses.get(mes_nome[:3], '01')
                data = f"{dia}/{mes}"
            else:
                data = data_completa[:5]

            def parse_num(s: str) -> int:
                s = s.strip().replace('.', '').replace(',', '')
                s = ''.join(c for c in s if c.isdigit())
                return int(s) if s else 0

            # Colunas: DATA, REF, CARTAS, BONUS, QTD, MIN, MED, MAX, TOTAL
            # Indices:  0     1     2       3      4    5    6    7    8
            refinamento = colunas[1] if len(colunas) > 1 else "Nao refinado"
            cartas = colunas[2] if len(colunas) > 2 else "Nenhuma"
            bonus = colunas[3] if len(colunas) > 3 else "Nenhum"
            quantidade = parse_num(colunas[4]) if len(colunas) > 4 else 0
            preco_min = parse_num(colunas[5]) if len(colunas) > 5 else 0
            preco_medio = parse_num(colunas[6]) if len(colunas) > 6 else 0
            preco_max = parse_num(colunas[7]) if len(colunas) > 7 else 0
            total_vendido = parse_num(colunas[8]) if len(colunas) > 8 else 0

            return PriceHistoryEntry(
                data=data,
                data_completa=data_completa,
                refinamento=refinamento,
                cartas=cartas,
                bonus=bonus,
                quantidade=quantidade,
                preco_min=preco_min,
                preco_medio=preco_medio,
                preco_max=preco_max,
                total_vendido=total_vendido
            )
        except Exception as e:
            logger.debug(f"Erro ao parsear texto do historico: {str(e)}")
            return None

    def _get_all_offers(self) -> List[ItemOffer]:
        """
        Obtem todas as ofertas das lojas

        Returns:
            Lista de ItemOffer
        """
        ofertas = []

        try:
            # Clica no botao de lojas - busca iterando pelos botoes
            shops_button = None
            botoes = self.page.eles('tag:button')
            for btn in botoes:
                if btn.text and 'lojas' in btn.text.lower():
                    shops_button = btn
                    break

            if not shops_button:
                # Fallback: tenta XPath direto
                shops_button = self.page.ele('xpath://button[contains(., "lojas")]', timeout=5)

            # Scrolla e clica via JavaScript (mais confiavel)
            shops_button.scroll.to_center()
            time.sleep(1)
            self.page.run_js('arguments[0].click()', shops_button)

            # Espera as ofertas carregarem
            time.sleep(Settings.SHOPS_TIMEOUT)

            # Busca containers das lojas
            lojas_elements = self.page.eles(
                "css:.rounded-sm.bg-white.text-black.px-4.py-2.text-base"
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

        except ElementNotFoundError:
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
                # Padrao item simples: nao tem [slots], mas tem (id:)
                # Inclui cartas quando NAO estiver na secao "Cartas Equipadas:"
                elif re.match(r'^[A-Z].*\(id:\s*\d+\)', linha_strip) and '[' not in linha_strip:
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
        is_context_manager = self.page is not None

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

            # Obtem historico de precos ANTES de clicar em lojas
            # (o botao de lojas pode mudar a visualizacao da pagina)
            price_history = self._get_price_history(item_name)

            # Obtem todas as ofertas (clica no botao de lojas)
            ofertas = self._get_all_offers()

            if not ofertas:
                raise ItemNotFoundException(item_name)

            # Usa o nome real do item (da primeira oferta) em vez do termo buscado
            nome_real = ofertas[0].nome if ofertas else item_name

            # Atualiza o nome do item no historico se ja foi obtido
            if price_history:
                price_history.item_nome = nome_real

            result = ItemSearchResult(
                item_nome=nome_real,
                ofertas=ofertas,
                preco_medio=preco_medio,
                volume_vendas=volume_vendas,
                price_history=price_history
            )

            logger.info(f"Busca concluida: {len(ofertas)} ofertas para '{item_name}'")
            return result

        except ItemNotFoundException:
            raise

        except (BrowserException, PageLoadException, ScraperException):
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
