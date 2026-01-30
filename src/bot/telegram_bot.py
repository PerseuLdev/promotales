"""Bot do Telegram para o PromoTales"""

import re
from typing import Optional, Dict
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters
)

from ..config.settings import Settings
from ..scraper.ragnatales_scraper import RagnatalesScraper
from ..models.item_offer import ItemSearchResult
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
        self.app: Optional[ApplicationBuilder] = None

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
            "*Botoes de refinamento:*\n"
            "Mostra cada refino disponivel (+0, +4, +7, +9, etc)\n\n"
            "*Comandos disponiveis:*\n"
            "/start - Inicia o bot\n"
            "/help - Mostra esta mensagem\n\n"
            "*Limites:*\n"
            "⚠️ Maximo de 5 buscas por minuto"
        )
        await update.message.reply_text(help_message, parse_mode='Markdown')

    def _create_refinement_keyboard(self, result: ItemSearchResult, localizacao: str = "") -> InlineKeyboardMarkup:
        """Cria teclado inline com opcoes de refinamento individuais"""
        refinos = result.refinamentos_disponiveis()

        buttons = []
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

        # Botao de mais barato geral
        buttons.append([InlineKeyboardButton("💰 Mais Barato (qualquer)", callback_data="ref_any")])

        # Botao de copiar localizacao (se disponivel)
        if localizacao:
            buttons.append([InlineKeyboardButton(f"📋 Copiar: {localizacao}", callback_data=f"copy_{localizacao}")])

        return InlineKeyboardMarkup(buttons)

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

            # Armazena no context.user_data
            context.user_data['last_search'] = result

            # Deleta mensagem de status
            await status_msg.delete()

            # Se especificou refinamento, mostra direto
            if ref_especifico is not None:
                oferta = result.mais_barato(ref_especifico)
                if oferta:
                    response = oferta.to_message(mostrar_detalhes=True)
                    if result.preco_medio:
                        response += f"\n\n📊 *Media 45d:* {result.preco_medio} zenys"

                    keyboard = self._create_refinement_keyboard(result, oferta.localizacao)
                    await update.message.reply_text(response, reply_markup=keyboard, parse_mode='Markdown')
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

                localizacao = mais_barato.localizacao if mais_barato else ""
                keyboard = self._create_refinement_keyboard(result, localizacao)
                await update.message.reply_text(
                    response,
                    reply_markup=keyboard,
                    parse_mode='Markdown'
                )

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

        # Recupera busca do context.user_data
        result = context.user_data.get('last_search')
        if not result:
            await query.edit_message_text(
                "❌ Busca expirada. Por favor, faca uma nova busca."
            )
            return

        # Extrai refinamento do callback: ref_0, ref_7, ref_any
        data = query.data
        refino_str = data.replace("ref_", "")

        if refino_str == "any":
            oferta = result.mais_barato()
            faixa_texto = "qualquer refinamento"
        else:
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

            keyboard = self._create_refinement_keyboard(result, oferta.localizacao)
            await query.edit_message_text(
                response,
                reply_markup=keyboard,
                parse_mode='Markdown'
            )
        else:
            await query.edit_message_text(
                f"❌ Nenhuma oferta encontrada para {faixa_texto}.\n\n"
                f"Refinamentos disponiveis: {', '.join(f'+{r}' for r in result.refinamentos_disponiveis())}"
            )

    async def handle_copy_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handler para callback do botao de copiar localizacao"""
        query = update.callback_query

        # Extrai localizacao do callback: copy_@market 123/456
        data = query.data
        localizacao = data.replace("copy_", "")

        if localizacao:
            await query.answer(f"📋 {localizacao}", show_alert=True)
        else:
            await query.answer("❌ Localizacao nao encontrada")

    async def error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handler de erros globais"""
        logger.error(f"Erro capturado: {context.error}", exc_info=context.error)

        if update and update.message:
            await update.message.reply_text(
                "❌ Ocorreu um erro inesperado. Por favor, tente novamente."
            )

    def setup_handlers(self) -> None:
        """Configura os handlers do bot"""
        self.app.add_handler(CommandHandler("start", self.start_command))
        self.app.add_handler(CommandHandler("help", self.help_command))
        self.app.add_handler(CallbackQueryHandler(self.handle_refinement_callback, pattern="^ref_"))
        self.app.add_handler(CallbackQueryHandler(self.handle_copy_callback, pattern="^copy_"))
        self.app.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message)
        )
        self.app.add_error_handler(self.error_handler)
        logger.info("Handlers configurados com sucesso")

    def run(self) -> None:
        """Inicia o bot"""
        self.app = ApplicationBuilder().token(Settings.BOT_TOKEN).build()
        self.setup_handlers()

        # Log de informacoes de ambiente
        if Settings.IS_RENDER:
            logger.info("🚀 Bot rodando no Render (modo producao)")
        else:
            logger.info("🛠️ Bot rodando localmente (modo desenvolvimento)")

        logger.info("✅ Bot iniciado com sucesso. Aguardando mensagens...")
        self.app.run_polling()
