"""Bot do Telegram para o PromoTales"""

import re
import asyncio
from typing import Optional, Dict
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters
)

from ..config.settings import Settings
from ..scraper.ragnatales_scraper import RagnatalesScraper
from ..models.item_offer import ItemSearchResult
from ..services.monitor_service import MonitorService, MIN_INTERVAL_MINUTES, MAX_ITEMS_PER_USER
from ..services.cache_service import MemoryCache, BaseCache
from ..services.browser_pool import get_browser_manager, BrowserManager


def create_cache() -> BaseCache:
    """Factory para criar cache baseado na configuração."""
    if Settings.CACHE_TYPE == "sqlite":
        from ..services.sqlite_cache import SQLiteCache
        return SQLiteCache(
            db_path=Settings.SQLITE_DB_PATH,
            default_ttl=Settings.CACHE_TTL
        )
    return MemoryCache(default_ttl=Settings.CACHE_TTL)
from ..services.job_queue import LocalJobQueue, SearchJob, JobStatus
from ..services.search_worker import SearchWorker
from ..exceptions import (
    InvalidItemNameException,
    RateLimitExceededException,
    ItemNotFoundException,
    PromoTalesException
)
from ..utils.logger import get_logger
from ..utils.validators import validate_item_name
from ..utils.rate_limiter import global_rate_limiter

logger = get_logger(__name__)


class TelegramBot:
    """Classe principal do bot do Telegram"""

    def __init__(self) -> None:
        """Inicializa o bot"""
        Settings.validate()
        self.monitor_service: MonitorService = MonitorService()
        self.app: Optional[Application] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None

        # Cache e Browser Pool
        self.cache: BaseCache = create_cache()
        self.browser_manager: BrowserManager = get_browser_manager()

        # Job Queue e Worker
        self.job_queue: LocalJobQueue = LocalJobQueue(max_size=Settings.MAX_QUEUE_SIZE)
        self.worker: SearchWorker = SearchWorker(
            job_queue=self.job_queue,
            cache=self.cache,
            browser_manager=self.browser_manager,
            result_callback=self._on_job_completed
        )

        # Mapa de jobs pendentes: job_id -> (chat_id, message_id, user_data_key)
        self._pending_jobs: Dict[str, tuple] = {}

        logger.info(f"Cache inicializado: {Settings.CACHE_TYPE} (TTL: {Settings.CACHE_TTL}s)")
        logger.info(f"BrowserManager inicializado (headless: {Settings.HEADLESS})")
        logger.info(f"JobQueue inicializada (max_size: {Settings.MAX_QUEUE_SIZE})")

    def _on_job_completed(self, job: SearchJob) -> None:
        """
        Callback chamado pelo worker quando um job termina.
        Executa em thread separada, então usa asyncio para comunicar com o bot.
        """
        if self._loop is None:
            logger.warning("Event loop não disponível para callback")
            return

        # Agenda a coroutine no event loop do bot
        asyncio.run_coroutine_threadsafe(
            self._handle_job_result(job),
            self._loop
        )

    async def _handle_job_result(self, job: SearchJob) -> None:
        """Processa resultado de um job e atualiza a mensagem do Telegram."""
        job_info = self._pending_jobs.pop(job.job_id, None)
        if not job_info:
            logger.warning(f"Job {job.job_id} não encontrado em pending_jobs")
            return

        chat_id, message_id, user_data_key, ref_especifico = job_info

        try:
            if job.status == JobStatus.COMPLETED and job.result:
                result = job.result
                await self._send_search_result(
                    chat_id=chat_id,
                    message_id=message_id,
                    result=result,
                    ref_especifico=ref_especifico,
                    user_data_key=user_data_key
                )
            elif job.status == JobStatus.FAILED:
                error_msg = job.error or "Erro desconhecido"
                await self.app.bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=message_id,
                    text=f"❌ {error_msg}"
                )
            else:
                await self.app.bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=message_id,
                    text="❌ A busca foi cancelada."
                )
        except Exception as e:
            logger.error(f"Erro ao processar resultado do job {job.job_id}: {e}")

    async def _send_search_result(
        self,
        chat_id: int,
        message_id: int,
        result: ItemSearchResult,
        ref_especifico: Optional[int],
        user_data_key: str
    ) -> None:
        """Envia/edita mensagem com resultado da busca."""
        # Armazena resultado para callbacks (usa application.bot_data como storage global)
        self.app.bot_data[user_data_key] = result

        if ref_especifico is not None:
            oferta = result.mais_barato(ref_especifico)
            if oferta:
                response = oferta.to_message(mostrar_detalhes=True)
                if result.preco_medio:
                    response += f"\n\n📊 *Media 45d:* {result.preco_medio} zenys"

                keyboard = self._create_refinement_keyboard(result)
                await self.app.bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=message_id,
                    text=response,
                    reply_markup=keyboard,
                    parse_mode='Markdown'
                )
            else:
                refinos_disp = ', '.join(f'+{r}' for r in result.refinamentos_disponiveis())
                await self.app.bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=message_id,
                    text=f"❌ Nenhum '{result.item_nome}' com refinamento +{ref_especifico} encontrado.\n\n"
                         f"Refinamentos disponiveis: {refinos_disp}"
                )
        else:
            # Mostra resumo com botoes
            mais_barato = result.mais_barato()
            response = result.resumo()

            # Se tem cartas ou bonus, mostra detalhes do mais barato
            if mais_barato and (mais_barato.cartas or mais_barato.bonus_aleatorios):
                response += "\n\n📦 *Detalhes do mais barato:*\n"
                if mais_barato.cartas:
                    response += f"💎 Cartas: {', '.join(mais_barato.cartas)}\n"
                if mais_barato.bonus_aleatorios:
                    for bonus in mais_barato.bonus_aleatorios:
                        response += f"✨ {bonus}\n"

            # Media no final
            if result.preco_medio:
                response += f"\n📊 *Media 45d:* {result.preco_medio} zenys"

            keyboard = self._create_refinement_keyboard(result)
            await self.app.bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=response,
                reply_markup=keyboard,
                parse_mode='Markdown'
            )

        logger.info(f"Resultado enviado para chat {chat_id}")

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handler do comando /start"""
        user = update.effective_user
        logger.info(f"Comando /start recebido de {user.username} (ID: {user.id})")

        welcome_message = (
            "👋 Bem-vindo ao PromoTales Bot!\n\n"
            "Envie o nome de um item para buscar o melhor preco no market do Ragnatales!\n\n"
            "📝 Exemplos:\n"
            "• `manto da bruxa` - busca geral\n"
            "• `+9 manto da bruxa` - busca com refinamento\n\n"
            "⚠️ Limite: 5 buscas por minuto"
        )
        await update.message.reply_text(welcome_message, parse_mode='Markdown')

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handler do comando /help"""
        logger.info(f"Comando /help recebido de {update.effective_user.username}")

        help_message = (
            "📖 *Como usar o PromoTales Bot*\n\n"
            "1️⃣ Digite o nome do item que voce quer buscar\n"
            "2️⃣ Aguarde alguns segundos\n"
            "3️⃣ Use os botoes para filtrar por refinamento\n\n"
            "*Busca com refinamento:*\n"
            "• `+9 manto da bruxa` - busca direto +9\n"
            "• `manto da bruxa +7` - busca direto +7\n\n"
            "*Comandos de busca:*\n"
            "/start - Inicia o bot\n"
            "/help - Mostra esta mensagem\n\n"
            "*Comandos de monitoramento:*\n"
            "`/monitor <item>, <min>[, alertas]`\n"
            "`/atualizar <item>, <min>[, alertas]`\n"
            "/lista - Lista itens monitorados\n"
            "/remover <item> - Remove monitoramento\n\n"
            "*Exemplos de monitoramento:*\n"
            "• `/monitor manto, 30` - simples\n"
            "• `/monitor +10 vestido, 15, -50%` - alerta queda\n"
            "• `/monitor cajado, 15, +30%` - alerta subida\n"
            "• `/monitor anel, 20, -20%, +50%` - ambos\n"
            "• `/monitor item, 15, 100000000` - preco alvo\n"
            "• `/atualizar manto, 10, -25%` - atualiza\n\n"
            "*Limites:*\n"
            f"⚠️ Max 5 buscas/min | Max {MAX_ITEMS_PER_USER} itens monitorados"
        )
        await update.message.reply_text(help_message, parse_mode='Markdown')

    async def comandos_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handler do comando /comandos - alias para /help"""
        await self.help_command(update, context)

    def _create_refinement_keyboard(self, result: ItemSearchResult) -> InlineKeyboardMarkup:
        """Cria teclado inline com opcoes de refinamento individuais"""
        buttons = []

        # So mostra botoes de refinamento para equipamentos
        if result.is_equipamento():
            refinos = result.refinamentos_disponiveis()
            row = []

            # Cria botao para cada refino disponivel
            for refino in sorted(refinos):
                label = f"+{refino}" if refino > 0 else "+0"
                row.append(InlineKeyboardButton(label, callback_data=f"ref_{refino}"))

                # 4 botoes por linha
                if len(row) >= 4:
                    buttons.append(row)
                    row = []

            # Adiciona ultima linha se houver botoes
            if row:
                buttons.append(row)

        # Adiciona botao de analise de mercado (se tiver historico)
        if result.price_history:
            buttons.append([InlineKeyboardButton("📊 Análise de Mercado", callback_data="analysis")])

        # Adiciona botao com link do produto (usa primeira oferta que tenha link)
        link = next((o.link for o in result.ofertas if o.link), None)
        if link:
            buttons.append([InlineKeyboardButton("🔗 Ver no site", url=link)])

        return InlineKeyboardMarkup(buttons) if buttons else None

    def _parse_refinement_from_query(self, item_name: str) -> tuple[str, Optional[int]]:
        """
        Extrai refinamento do nome do item

        Args:
            item_name: Nome com possivel refinamento (+9 manto ou manto +9)

        Returns:
            Tuple (nome_limpo, refinamento ou None)
        """
        # Pattern: +9 no inicio
        match_inicio = re.match(r'^\+(\d+)\s*(.+)$', item_name)
        if match_inicio:
            return match_inicio.group(2).strip(), int(match_inicio.group(1))

        # Pattern: +9 no final
        match_final = re.match(r'^(.+?)\s*\+(\d+)$', item_name)
        if match_final:
            return match_final.group(1).strip(), int(match_final.group(2))

        return item_name, None

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handler de mensagens de texto (busca de itens)"""
        user = update.effective_user
        chat_id = update.effective_chat.id
        item_name = update.message.text.strip()

        logger.info(f"Busca de item '{item_name}' solicitada por {user.username} (ID: {user.id})")

        try:
            # Verifica rate limit
            global_rate_limiter.check_rate_limit(user.id)

            # Valida e sanitiza o nome do item
            sanitized_name = validate_item_name(item_name)

            # Extrai refinamento se especificado
            nome_busca, ref_especifico = self._parse_refinement_from_query(sanitized_name)

            logger.info(f"Nome: '{nome_busca}', Refinamento: {ref_especifico}")

            # Verifica cache primeiro (retorno imediato se encontrado)
            cache_key = nome_busca
            cached_result = self.cache.get(cache_key)

            if cached_result:
                logger.info(f"Cache HIT para '{nome_busca}'")
                # Retorno imediato do cache
                await self._send_cached_result(
                    update=update,
                    context=context,
                    result=cached_result,
                    ref_especifico=ref_especifico
                )
                return

            # Cache MISS - enfileira job para processamento em background
            logger.info(f"Cache MISS para '{nome_busca}', enfileirando job...")

            # Mensagem de processamento (será editada quando o resultado chegar)
            remaining = global_rate_limiter.get_remaining_requests(user.id)
            pending_jobs = self.job_queue.pending_count

            status_text = f"🔎 Buscando '{nome_busca}'...\n"
            if pending_jobs > 0:
                status_text += f"📋 Posicao na fila: {pending_jobs + 1}\n"
            status_text += f"📊 Buscas restantes: {remaining}/{global_rate_limiter.max_requests}"

            status_msg = await update.message.reply_text(status_text)

            # Cria job
            job = SearchJob(
                item_name=nome_busca,
                chat_id=chat_id,
                user_id=user.id,
                message_id=status_msg.message_id,
                refinamento=ref_especifico
            )

            # Chave para armazenar resultado (para callbacks de refinamento)
            user_data_key = f'search_{status_msg.message_id}'

            # Registra job pendente
            self._pending_jobs[job.job_id] = (chat_id, status_msg.message_id, user_data_key, ref_especifico)

            # Enfileira job
            if not self.job_queue.enqueue(job):
                # Fila cheia
                del self._pending_jobs[job.job_id]
                await status_msg.edit_text(
                    "❌ Servidor ocupado. Por favor, tente novamente em alguns segundos."
                )
                return

            logger.info(f"Job {job.job_id} enfileirado para '{nome_busca}'")

        except RateLimitExceededException as e:
            error_msg = (
                f"⏳ {e.message}\n\n"
                f"⏰ Voce podera fazer outra busca em breve."
            )
            logger.warning(f"Rate limit excedido para usuario {user.id}")
            await update.message.reply_text(error_msg)

        except InvalidItemNameException as e:
            error_msg = f"❌ {e.message}\n\nPor favor, verifique o nome e tente novamente."
            logger.warning(f"Nome de item invalido: '{item_name}' - {e.reason}")
            await update.message.reply_text(error_msg)

        except Exception as e:
            error_msg = f"❌ Erro inesperado ao buscar '{item_name}'. Tente novamente mais tarde."
            logger.error(f"Erro nao tratado ao processar busca: {str(e)}", exc_info=True)
            await update.message.reply_text(error_msg)

    async def _send_cached_result(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        result: ItemSearchResult,
        ref_especifico: Optional[int]
    ) -> None:
        """Envia resultado do cache imediatamente (sem passar pela fila)."""
        if ref_especifico is not None:
            oferta = result.mais_barato(ref_especifico)
            if oferta:
                response = oferta.to_message(mostrar_detalhes=True)
                if result.preco_medio:
                    response += f"\n\n📊 *Media 45d:* {result.preco_medio} zenys"

                keyboard = self._create_refinement_keyboard(result)
                sent_msg = await update.message.reply_text(
                    response,
                    reply_markup=keyboard,
                    parse_mode='Markdown'
                )
                context.user_data[f'search_{sent_msg.message_id}'] = result
            else:
                refinos_disp = ', '.join(f'+{r}' for r in result.refinamentos_disponiveis())
                await update.message.reply_text(
                    f"❌ Nenhum '{result.item_nome}' com refinamento +{ref_especifico} encontrado.\n\n"
                    f"Refinamentos disponiveis: {refinos_disp}"
                )
        else:
            # Mostra resumo com botoes
            mais_barato = result.mais_barato()
            response = result.resumo()

            # Se tem cartas ou bonus, mostra detalhes do mais barato
            if mais_barato and (mais_barato.cartas or mais_barato.bonus_aleatorios):
                response += "\n\n📦 *Detalhes do mais barato:*\n"
                if mais_barato.cartas:
                    response += f"💎 Cartas: {', '.join(mais_barato.cartas)}\n"
                if mais_barato.bonus_aleatorios:
                    for bonus in mais_barato.bonus_aleatorios:
                        response += f"✨ {bonus}\n"

            # Media no final
            if result.preco_medio:
                response += f"\n📊 *Media 45d:* {result.preco_medio} zenys"

            keyboard = self._create_refinement_keyboard(result)
            sent_msg = await update.message.reply_text(
                response,
                reply_markup=keyboard,
                parse_mode='Markdown'
            )
            context.user_data[f'search_{sent_msg.message_id}'] = result

        logger.info(f"Resultado do cache enviado para '{result.item_nome}'")

    def _get_search_result(self, context: ContextTypes.DEFAULT_TYPE, message_id: int) -> Optional[ItemSearchResult]:
        """
        Busca resultado de busca em user_data ou bot_data.

        Resultados de cache vão para user_data.
        Resultados da fila vão para bot_data.
        """
        key = f'search_{message_id}'
        # Tenta user_data primeiro (cache hit)
        result = context.user_data.get(key)
        if result:
            return result
        # Tenta bot_data (resultado da fila)
        return context.bot_data.get(key)

    async def handle_refinement_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handler para callbacks dos botoes de refinamento"""
        query = update.callback_query

        await query.answer()

        # Recupera busca pelo ID da mensagem
        message_id = query.message.message_id
        result = self._get_search_result(context, message_id)
        if not result:
            await query.edit_message_text(
                "❌ Busca expirada. Por favor, faca uma nova busca."
            )
            return

        # Extrai refinamento do callback: ref_0, ref_7, etc
        data = query.data
        refino_str = data.replace("ref_", "")

        try:
            refino = int(refino_str)
            oferta = result.mais_barato(refino)
            faixa_texto = f"+{refino}" if refino > 0 else "+0 (sem refino)"
        except ValueError:
            oferta = result.mais_barato()
            faixa_texto = "geral"

        if oferta:
            response = f"🔍 *{result.item_nome}* ({faixa_texto})\n\n"
            response += oferta.to_message(mostrar_detalhes=True)

            if result.preco_medio:
                response += f"\n\n📊 *Media 45d:* {result.preco_medio} zenys"

            keyboard = self._create_refinement_keyboard(result)
            await query.edit_message_text(
                response,
                reply_markup=keyboard,
                parse_mode='Markdown'
            )
        else:
            keyboard = self._create_refinement_keyboard(result)
            await query.edit_message_text(
                f"❌ Nenhuma oferta encontrada para {faixa_texto}.\n\n"
                f"Refinamentos disponiveis: {', '.join(f'+{r}' for r in result.refinamentos_disponiveis())}",
                reply_markup=keyboard
            )

    async def handle_analysis_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handler para callback do botao de analise de mercado"""
        query = update.callback_query
        await query.answer()

        # Recupera busca pelo ID da mensagem
        message_id = query.message.message_id
        result = self._get_search_result(context, message_id)

        if not result:
            await query.edit_message_text(
                "❌ Busca expirada. Por favor, faca uma nova busca."
            )
            return

        if not result.price_history:
            keyboard = self._create_refinement_keyboard(result)
            await query.edit_message_text(
                "❌ Historico de precos nao disponivel para este item.",
                reply_markup=keyboard
            )
            return

        # Obtem preco atual (mais barato)
        mais_barato = result.mais_barato()
        preco_atual = mais_barato.preco if mais_barato else 0

        # Gera mensagem de analise
        response = result.price_history.to_analysis_message(preco_atual)

        # Adiciona botao para voltar
        buttons = [[InlineKeyboardButton("⬅️ Voltar", callback_data="back_to_result")]]

        # Adiciona link do produto
        link = next((o.link for o in result.ofertas if o.link), None)
        if link:
            buttons.append([InlineKeyboardButton("🔗 Ver no site", url=link)])

        keyboard = InlineKeyboardMarkup(buttons)

        await query.edit_message_text(
            response,
            reply_markup=keyboard,
            parse_mode='Markdown'
        )

    async def handle_back_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handler para callback do botao de voltar"""
        query = update.callback_query
        await query.answer()

        # Recupera busca pelo ID da mensagem
        message_id = query.message.message_id
        result = self._get_search_result(context, message_id)

        if not result:
            await query.edit_message_text(
                "❌ Busca expirada. Por favor, faca uma nova busca."
            )
            return

        # Reconstroi a mensagem de resumo
        mais_barato = result.mais_barato()
        response = result.resumo()

        # Se tem cartas ou bonus, mostra detalhes do mais barato
        if mais_barato and (mais_barato.cartas or mais_barato.bonus_aleatorios):
            response += "\n\n📦 *Detalhes do mais barato:*\n"
            if mais_barato.cartas:
                response += f"💎 Cartas: {', '.join(mais_barato.cartas)}\n"
            if mais_barato.bonus_aleatorios:
                for bonus in mais_barato.bonus_aleatorios:
                    response += f"✨ {bonus}\n"

        # Media no final
        if result.preco_medio:
            response += f"\n📊 *Media 45d:* {result.preco_medio} zenys"

        keyboard = self._create_refinement_keyboard(result)
        await query.edit_message_text(
            response,
            reply_markup=keyboard,
            parse_mode='Markdown'
        )

    def _parse_monitor_args(self, text: str) -> tuple[Optional[str], Optional[int], Optional[float], Optional[float], Optional[int], Optional[str]]:
        """
        Parseia argumentos do comando /monitor

        Formato: /monitor <item>, <minutos>[, <alertas>]
        Alertas podem ser: -50% (queda), +30% (subida), 150000000 (preço alvo)
        Pode ter múltiplos alertas separados por vírgula

        Returns:
            tuple: (item_name, interval, alert_drop, alert_rise, alert_target, error_msg)
        """
        # Remove o comando /monitor do início se presente
        if text.startswith('/monitor'):
            text = text[8:].strip()

        if not text:
            return None, None, None, None, None, "Argumentos não fornecidos"

        # Divide por vírgulas
        parts = [p.strip() for p in text.split(',')]

        if len(parts) < 2:
            return None, None, None, None, None, "Formato inválido. Use: /monitor <item>, <minutos>[, <alertas>]"

        item_name = parts[0].strip()
        if not item_name:
            return None, None, None, None, None, "Nome do item não pode estar vazio"

        # Segundo parâmetro é o intervalo
        try:
            interval = int(parts[1].strip())
        except ValueError:
            return None, None, None, None, None, f"Intervalo inválido: '{parts[1]}'. Deve ser um número em minutos."

        # Parâmetros opcionais de alerta
        alert_drop = None
        alert_rise = None
        alert_target = None

        for part in parts[2:]:
            part = part.strip()
            if not part:
                continue

            # Alerta de queda: -50% ou -50
            if part.startswith('-'):
                try:
                    value = part[1:].replace('%', '').strip()
                    alert_drop = float(value)
                    if alert_drop <= 0 or alert_drop > 100:
                        return None, None, None, None, None, f"Percentual de queda inválido: {part}. Use valores entre 1 e 100."
                except ValueError:
                    return None, None, None, None, None, f"Valor de alerta inválido: {part}"

            # Alerta de subida: +30% ou +30
            elif part.startswith('+'):
                try:
                    value = part[1:].replace('%', '').strip()
                    alert_rise = float(value)
                    if alert_rise <= 0:
                        return None, None, None, None, None, f"Percentual de subida inválido: {part}. Use valores positivos."
                except ValueError:
                    return None, None, None, None, None, f"Valor de alerta inválido: {part}"

            # Alerta de preço alvo (número absoluto)
            else:
                try:
                    alert_target = int(part.replace('.', '').replace(',', ''))
                    if alert_target <= 0:
                        return None, None, None, None, None, f"Preço alvo inválido: {part}. Use valores positivos."
                except ValueError:
                    return None, None, None, None, None, f"Valor de alerta inválido: {part}"

        return item_name, interval, alert_drop, alert_rise, alert_target, None

    async def monitor_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handler do comando /monitor <item>, <minutos>[, <alertas>]"""
        user = update.effective_user
        chat_id = update.effective_chat.id

        logger.info(f"Comando /monitor recebido de {user.username} (ID: {user.id})")

        # Pega o texto completo após o comando
        full_text = update.message.text

        # Parseia os argumentos
        item_name, interval, alert_drop, alert_rise, alert_target, error = self._parse_monitor_args(full_text)

        if error:
            await update.message.reply_text(
                f"❌ {error}\n\n"
                "*Uso correto:*\n"
                "`/monitor <item>, <minutos>[, <alertas>]`\n\n"
                "*Exemplos:*\n"
                "`/monitor manto da bruxa, 30`\n"
                "`/monitor +10 vestido da bruxa, 15, -50%`\n"
                "`/monitor cajado corrompido, 15, +30%, -20%`\n"
                "`/monitor anel temporal, 20, 150000000`\n\n"
                "*Alertas disponiveis:*\n"
                "• `-X%` - Alerta quando cair X% do preco base\n"
                "• `+X%` - Alerta quando subir X% do preco base\n"
                "• `valor` - Alerta quando chegar no preco alvo\n\n"
                f"⏱️ Intervalo minimo: {MIN_INTERVAL_MINUTES} minutos\n"
                f"📦 Maximo de itens: {MAX_ITEMS_PER_USER}",
                parse_mode='Markdown'
            )
            return

        # Mensagem de processamento
        status_msg = await update.message.reply_text(
            f"⏳ Configurando monitoramento de '{item_name}'..."
        )

        # Adiciona monitoramento
        success, message = await self.monitor_service.add_monitor(
            application=self.app,
            user_id=user.id,
            chat_id=chat_id,
            item_name=item_name,
            interval_minutes=interval,
            alert_drop_percent=alert_drop,
            alert_rise_percent=alert_rise,
            alert_target_price=alert_target
        )

        await status_msg.delete()

        if success:
            await update.message.reply_text(
                f"✅ {message}\n\n"
                f"Voce sera notificado quando o preco mudar.",
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text(f"❌ {message}", parse_mode='Markdown')

    async def lista_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handler do comando /lista - lista itens monitorados"""
        user = update.effective_user

        logger.info(f"Comando /lista recebido de {user.username} (ID: {user.id})")

        items = self.monitor_service.list_monitors(user.id)

        if not items:
            await update.message.reply_text(
                "📭 Voce nao tem itens monitorados.\n\n"
                f"Use `/monitor <item>, <minutos>` para adicionar.",
                parse_mode='Markdown'
            )
            return

        response = "📋 *Itens Monitorados:*\n\n"
        for i, item in enumerate(items, 1):
            preco_str = f"{item.last_price:,}z".replace(",", ".") if item.last_price else "N/A"
            base_str = f"{item.base_price:,}z".replace(",", ".") if item.base_price else "N/A"
            response += (
                f"{i}. *{item.item_name}*\n"
                f"   ⏱️ A cada {item.interval_minutes} min\n"
                f"   💰 Preco atual: {preco_str}\n"
                f"   📍 Preco base: {base_str}\n"
            )
            if item.has_alerts_configured():
                response += f"   🔔 {item.alerts_summary()}\n"
            response += "\n"

        response += f"_Total: {len(items)}/{MAX_ITEMS_PER_USER} itens_"

        await update.message.reply_text(response, parse_mode='Markdown')

    async def remover_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handler do comando /remover <item>"""
        user = update.effective_user

        logger.info(f"Comando /remover recebido de {user.username} (ID: {user.id})")

        if not context.args:
            # Mostra lista para ajudar
            items = self.monitor_service.list_monitors(user.id)
            if items:
                lista = '\n'.join(f"• `{item.item_name}`" for item in items)
                await update.message.reply_text(
                    "❌ *Uso correto:*\n"
                    "`/remover <nome do item>`\n\n"
                    "*Seus itens monitorados:*\n"
                    f"{lista}",
                    parse_mode='Markdown'
                )
            else:
                await update.message.reply_text(
                    "❌ Voce nao tem itens monitorados para remover."
                )
            return

        item_name = ' '.join(context.args)

        success, message = await self.monitor_service.remove_monitor(
            application=self.app,
            user_id=user.id,
            item_name=item_name
        )

        if success:
            await update.message.reply_text(f"✅ {message}")
        else:
            await update.message.reply_text(f"❌ {message}")

    async def atualizar_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handler do comando /atualizar <item>, <minutos>[, <alertas>]"""
        user = update.effective_user
        chat_id = update.effective_chat.id

        logger.info(f"Comando /atualizar recebido de {user.username} (ID: {user.id})")

        # Pega o texto completo após o comando
        full_text = update.message.text

        # Remove o comando /atualizar do início
        if full_text.startswith('/atualizar'):
            text = full_text[10:].strip()
        else:
            text = full_text.strip()

        if not text:
            # Mostra lista para ajudar
            items = self.monitor_service.list_monitors(user.id)
            if items:
                lista = '\n'.join(f"• `{item.item_name}` ({item.interval_minutes}min)" for item in items)
                await update.message.reply_text(
                    "❌ *Uso correto:*\n"
                    "`/atualizar <item>, <minutos>[, alertas]`\n\n"
                    "*Exemplos:*\n"
                    "`/atualizar manto da bruxa, 10`\n"
                    "`/atualizar manto da bruxa, 15, -30%`\n"
                    "`/atualizar manto, 20, -20%, +50%`\n\n"
                    "*Seus itens monitorados:*\n"
                    f"{lista}",
                    parse_mode='Markdown'
                )
            else:
                await update.message.reply_text(
                    "❌ Voce nao tem itens monitorados para atualizar."
                )
            return

        # Parseia os argumentos (reutiliza o parser do monitor)
        item_name, interval, alert_drop, alert_rise, alert_target, error = self._parse_monitor_args(full_text.replace('/atualizar', '/monitor'))

        if error:
            await update.message.reply_text(
                f"❌ {error}\n\n"
                "*Uso correto:*\n"
                "`/atualizar <item>, <minutos>[, alertas]`\n\n"
                "*Exemplos:*\n"
                "`/atualizar manto da bruxa, 10`\n"
                "`/atualizar manto, 15, -30%, +20%`",
                parse_mode='Markdown'
            )
            return

        # Atualiza monitoramento
        success, message = await self.monitor_service.update_monitor(
            application=self.app,
            user_id=user.id,
            chat_id=chat_id,
            item_name=item_name,
            interval_minutes=interval,
            alert_drop_percent=alert_drop,
            alert_rise_percent=alert_rise,
            alert_target_price=alert_target,
            clear_alerts=True  # Substitui alertas ao invés de adicionar
        )

        if success:
            await update.message.reply_text(f"✅ {message}", parse_mode='Markdown')
        else:
            await update.message.reply_text(f"❌ {message}", parse_mode='Markdown')

    async def error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handler de erros globais"""
        logger.error(f"Erro capturado: {context.error}", exc_info=context.error)

        if update and update.message:
            await update.message.reply_text(
                "❌ Ocorreu um erro inesperado. Por favor, tente novamente."
            )

    def setup_handlers(self) -> None:
        """Configura os handlers do bot"""
        # Comandos basicos
        self.app.add_handler(CommandHandler("start", self.start_command))
        self.app.add_handler(CommandHandler("help", self.help_command))
        self.app.add_handler(CommandHandler("comandos", self.comandos_command))

        # Comandos de monitoramento
        self.app.add_handler(CommandHandler("monitor", self.monitor_command))
        self.app.add_handler(CommandHandler("lista", self.lista_command))
        self.app.add_handler(CommandHandler("remover", self.remover_command))
        self.app.add_handler(CommandHandler("atualizar", self.atualizar_command))

        # Callbacks
        self.app.add_handler(CallbackQueryHandler(self.handle_refinement_callback, pattern="^ref_"))
        self.app.add_handler(CallbackQueryHandler(self.handle_analysis_callback, pattern="^analysis$"))
        self.app.add_handler(CallbackQueryHandler(self.handle_back_callback, pattern="^back_to_result$"))

        # Mensagens de texto (busca)
        self.app.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message)
        )

        self.app.add_error_handler(self.error_handler)
        logger.info("Handlers configurados com sucesso")

    async def shutdown(self, application: Application = None) -> None:
        """Cleanup ao encerrar o bot"""
        logger.info("Iniciando shutdown...")

        # Para o worker
        if self.worker.is_running():
            logger.info("Parando SearchWorker...")
            worker_stats = self.worker.stats
            logger.info(f"Worker stats finais: {worker_stats}")
            self.worker.stop(timeout=10.0)

        # Limpa cache
        cache_stats = self.cache.stats()
        logger.info(f"Cache stats finais: {cache_stats}")

        # Fecha conexão SQLite se aplicável
        if hasattr(self.cache, 'close'):
            self.cache.close()

        # Encerra browser
        self.browser_manager.shutdown()

        # Limpa pending jobs
        self._pending_jobs.clear()

        logger.info("Shutdown concluido")

    async def _post_init(self, application: Application) -> None:
        """Callback executado após inicialização do app (captura event loop)."""
        self._loop = asyncio.get_running_loop()
        self.worker.start()
        logger.info("SearchWorker iniciado")

    def run(self) -> None:
        """Inicia o bot"""
        self.app = ApplicationBuilder().token(Settings.BOT_TOKEN).build()
        self.setup_handlers()

        # Registra callbacks de ciclo de vida
        self.app.post_init = self._post_init
        self.app.post_shutdown = self.shutdown

        # Restaura jobs de monitoramento
        restored = self.monitor_service.restore_jobs(self.app)
        if restored > 0:
            logger.info(f"📡 {restored} monitoramento(s) restaurado(s)")

        # Log de informacoes de ambiente
        if Settings.IS_ORACLE:
            logger.info("🚀 Bot rodando no Oracle Cloud (modo producao)")
        elif Settings.IS_RENDER:
            logger.info("🚀 Bot rodando no Render (modo producao)")
        else:
            logger.info("🛠️ Bot rodando localmente (modo desenvolvimento)")

        # Log de cache, browser e fila
        logger.info(f"💾 Cache: {Settings.CACHE_TYPE} | TTL={Settings.CACHE_TTL}s")
        logger.info(f"📋 Fila: max_size={Settings.MAX_QUEUE_SIZE}")

        logger.info("✅ Bot iniciado com sucesso. Aguardando mensagens...")
        self.app.run_polling()
