"""Bot do Telegram para o PromoTales"""

import re
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
        self.scraper: RagnatalesScraper = RagnatalesScraper()
        self.monitor_service: MonitorService = MonitorService()
        self.app: Optional[Application] = None

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
            f"/monitor <item> <minutos> - Monitora item (min {MIN_INTERVAL_MINUTES}min)\n"
            "/lista - Lista itens monitorados\n"
            "/remover <item> - Remove monitoramento\n\n"
            "*Limites:*\n"
            f"⚠️ Max 5 buscas/min | Max {MAX_ITEMS_PER_USER} itens monitorados"
        )
        await update.message.reply_text(help_message, parse_mode='Markdown')

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

            # Mensagem de processamento
            remaining = global_rate_limiter.get_remaining_requests(user.id)
            status_msg = await update.message.reply_text(
                f"🔎 Buscando informacoes...\n"
                f"📊 Buscas restantes: {remaining}/{global_rate_limiter.max_requests}"
            )

            # Busca informacoes do item
            result = self.scraper.search_item(nome_busca)

            # Deleta mensagem de status
            await status_msg.delete()

            # Se especificou refinamento, mostra direto
            if ref_especifico is not None:
                oferta = result.mais_barato(ref_especifico)
                if oferta:
                    response = oferta.to_message(mostrar_detalhes=True)
                    if result.preco_medio:
                        response += f"\n\n📊 *Media 45d:* {result.preco_medio} zenys"

                    keyboard = self._create_refinement_keyboard(result)
                    sent_msg = await update.message.reply_text(response, reply_markup=keyboard, parse_mode='Markdown')
                    # Armazena resultado pelo ID da mensagem
                    context.user_data[f'search_{sent_msg.message_id}'] = result
                else:
                    await update.message.reply_text(
                        f"❌ Nenhum '{nome_busca}' com refinamento +{ref_especifico} encontrado.\n\n"
                        f"Refinamentos disponiveis: {', '.join(f'+{r}' for r in result.refinamentos_disponiveis())}"
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
                # Armazena resultado pelo ID da mensagem
                context.user_data[f'search_{sent_msg.message_id}'] = result

            logger.info(f"Busca de '{nome_busca}' concluida com sucesso")

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

        except ItemNotFoundException as e:
            logger.info(f"Item nao encontrado: '{e.item_name}'")
            await update.message.reply_text(e.message)

        except PromoTalesException as e:
            error_msg = f"❌ {e.message}"
            logger.error(f"Erro PromoTales: {str(e)}")
            await update.message.reply_text(error_msg)

        except Exception as e:
            error_msg = f"❌ Erro inesperado ao buscar '{item_name}'. Tente novamente mais tarde."
            logger.error(f"Erro nao tratado ao processar busca: {str(e)}", exc_info=True)
            await update.message.reply_text(error_msg)

    async def handle_refinement_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handler para callbacks dos botoes de refinamento"""
        query = update.callback_query

        await query.answer()

        # Recupera busca pelo ID da mensagem
        message_id = query.message.message_id
        result = context.user_data.get(f'search_{message_id}')
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
        result = context.user_data.get(f'search_{message_id}')

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
        result = context.user_data.get(f'search_{message_id}')

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

    async def monitor_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handler do comando /monitor <item> <minutos>"""
        user = update.effective_user
        chat_id = update.effective_chat.id

        logger.info(f"Comando /monitor recebido de {user.username} (ID: {user.id})")

        # Verifica argumentos
        if not context.args or len(context.args) < 2:
            await update.message.reply_text(
                "❌ *Uso correto:*\n"
                f"`/monitor <nome do item> <minutos>`\n\n"
                f"*Exemplo:*\n"
                f"`/monitor folha afiada 30`\n\n"
                f"⏱️ Intervalo minimo: {MIN_INTERVAL_MINUTES} minutos\n"
                f"📦 Maximo de itens: {MAX_ITEMS_PER_USER}",
                parse_mode='Markdown'
            )
            return

        # Extrai intervalo (ultimo argumento)
        try:
            interval = int(context.args[-1])
            item_name = ' '.join(context.args[:-1])
        except ValueError:
            await update.message.reply_text(
                "❌ O ultimo argumento deve ser o intervalo em minutos.\n\n"
                "*Exemplo:* `/monitor folha afiada 30`",
                parse_mode='Markdown'
            )
            return

        if not item_name:
            await update.message.reply_text("❌ Nome do item nao pode estar vazio.")
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
            interval_minutes=interval
        )

        await status_msg.delete()

        if success:
            await update.message.reply_text(
                f"✅ {message}\n\n"
                f"Voce sera notificado quando o preco mudar.",
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text(f"❌ {message}")

    async def lista_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handler do comando /lista - lista itens monitorados"""
        user = update.effective_user

        logger.info(f"Comando /lista recebido de {user.username} (ID: {user.id})")

        items = self.monitor_service.list_monitors(user.id)

        if not items:
            await update.message.reply_text(
                "📭 Voce nao tem itens monitorados.\n\n"
                f"Use `/monitor <item> <minutos>` para adicionar.",
                parse_mode='Markdown'
            )
            return

        response = "📋 *Itens Monitorados:*\n\n"
        for i, item in enumerate(items, 1):
            preco_str = f"{item.last_price:,}z".replace(",", ".") if item.last_price else "N/A"
            response += (
                f"{i}. *{item.item_name}*\n"
                f"   ⏱️ A cada {item.interval_minutes} min\n"
                f"   💰 Ultimo preco: {preco_str}\n\n"
            )

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

        # Comandos de monitoramento
        self.app.add_handler(CommandHandler("monitor", self.monitor_command))
        self.app.add_handler(CommandHandler("lista", self.lista_command))
        self.app.add_handler(CommandHandler("remover", self.remover_command))

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

    def run(self) -> None:
        """Inicia o bot"""
        self.app = ApplicationBuilder().token(Settings.BOT_TOKEN).build()
        self.setup_handlers()

        # Restaura jobs de monitoramento
        restored = self.monitor_service.restore_jobs(self.app)
        if restored > 0:
            logger.info(f"📡 {restored} monitoramento(s) restaurado(s)")

        # Log de informacoes de ambiente
        if Settings.IS_RENDER:
            logger.info("🚀 Bot rodando no Render (modo producao)")
        else:
            logger.info("🛠️ Bot rodando localmente (modo desenvolvimento)")

        logger.info("✅ Bot iniciado com sucesso. Aguardando mensagens...")
        self.app.run_polling()
