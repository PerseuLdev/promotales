"""Serviço de monitoramento de preços"""

from typing import Dict, Optional, List
from datetime import timedelta
from telegram.ext import Application, ContextTypes

from ..models.monitored_item import MonitoredItem, MonitorStorage
from ..scraper.ragnatales_scraper import RagnatalesScraper
from ..exceptions import ItemNotFoundException, ScraperException
from ..utils.logger import get_logger

logger = get_logger(__name__)

# Configurações
MIN_INTERVAL_MINUTES = 5
MAX_ITEMS_PER_USER = 10


class MonitorService:
    """Serviço para gerenciar monitoramento de itens"""

    def __init__(self, storage_path: str = "monitored_items.json"):
        self.storage = MonitorStorage(storage_path)
        self.scraper: Optional[RagnatalesScraper] = None
        self._jobs: Dict[str, object] = {}  # job_id -> job

    def _get_job_id(self, user_id: int, item_name: str) -> str:
        """Gera ID único para o job"""
        return f"monitor_{user_id}_{item_name.lower().replace(' ', '_')}"

    async def add_monitor(
        self,
        application: Application,
        user_id: int,
        chat_id: int,
        item_name: str,
        interval_minutes: int,
        alert_drop_percent: Optional[float] = None,
        alert_rise_percent: Optional[float] = None,
        alert_target_price: Optional[int] = None
    ) -> tuple[bool, str]:
        """
        Adiciona item para monitoramento

        Args:
            application: Aplicação do Telegram
            user_id: ID do usuário
            chat_id: ID do chat para notificações
            item_name: Nome do item
            interval_minutes: Intervalo em minutos
            alert_drop_percent: Alerta quando cair X% (ex: 50 = -50%)
            alert_rise_percent: Alerta quando subir X% (ex: 30 = +30%)
            alert_target_price: Alerta quando chegar no valor X

        Returns:
            tuple: (sucesso, mensagem)
        """
        # Validações
        if interval_minutes < MIN_INTERVAL_MINUTES:
            return False, f"Intervalo mínimo é {MIN_INTERVAL_MINUTES} minutos"

        user_items = self.storage.get_user_items(user_id)
        if len(user_items) >= MAX_ITEMS_PER_USER:
            return False, f"Limite de {MAX_ITEMS_PER_USER} itens por usuário"

        # Verifica se já existe
        existing = self.storage.get(user_id, item_name)
        if existing:
            return False, f"Item '{item_name}' já está sendo monitorado"

        # Cria item
        item = MonitoredItem(
            user_id=user_id,
            item_name=item_name,
            interval_minutes=interval_minutes,
            alert_drop_percent=alert_drop_percent,
            alert_rise_percent=alert_rise_percent,
            alert_target_price=alert_target_price
        )

        # Faz primeira busca para validar o item
        try:
            logger.info(f"Validando item '{item_name}' para usuário {user_id}")
            scraper = RagnatalesScraper()
            result = scraper.search_item(item_name)

            # Atualiza com preço inicial
            if result.ofertas:
                mais_barato = result.mais_barato()
                if mais_barato:
                    item.last_price = mais_barato.preco
                    item.base_price = mais_barato.preco  # Preço base para alertas

        except ItemNotFoundException:
            return False, f"Item '{item_name}' não encontrado no market"
        except ScraperException as e:
            return False, f"Erro ao buscar item: {str(e)}"

        # Salva no storage
        if not self.storage.add(item):
            return False, f"Erro ao salvar monitoramento"

        # Agenda job
        self._schedule_job(application, item, chat_id)

        logger.info(f"Monitoramento adicionado: {item_name} a cada {interval_minutes}min para usuário {user_id}")

        # Monta mensagem de resposta
        response = f"Monitorando '*{item_name}*' a cada {interval_minutes} minutos\n"
        response += f"💰 Preço base: {item.last_price:,}z\n".replace(",", ".")

        if item.has_alerts_configured():
            response += f"\n🔔 Alertas: {item.alerts_summary()}"

        return True, response

    def _schedule_job(self, application: Application, item: MonitoredItem, chat_id: int) -> None:
        """Agenda job de monitoramento"""
        job_id = self._get_job_id(item.user_id, item.item_name)

        # Remove job existente se houver
        self._remove_job(application, job_id)

        # Agenda novo job
        job = application.job_queue.run_repeating(
            callback=self._check_price_callback,
            interval=timedelta(minutes=item.interval_minutes),
            first=timedelta(minutes=item.interval_minutes),
            chat_id=chat_id,
            user_id=item.user_id,
            name=job_id,
            data={
                'user_id': item.user_id,
                'item_name': item.item_name,
                'chat_id': chat_id
            }
        )

        self._jobs[job_id] = job
        logger.debug(f"Job agendado: {job_id}")

    def _remove_job(self, application: Application, job_id: str) -> None:
        """Remove job existente"""
        if job_id in self._jobs:
            self._jobs[job_id].schedule_removal()
            del self._jobs[job_id]

        # Remove da fila do Telegram
        current_jobs = application.job_queue.get_jobs_by_name(job_id)
        for job in current_jobs:
            job.schedule_removal()

    async def _check_price_callback(self, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Callback executado pelo scheduler para verificar preço"""
        data = context.job.data
        user_id = data['user_id']
        item_name = data['item_name']
        chat_id = data['chat_id']

        logger.info(f"Verificando preço de '{item_name}' para usuário {user_id}")

        # Busca item do storage
        item = self.storage.get(user_id, item_name)
        if not item or not item.active:
            logger.warning(f"Item '{item_name}' não encontrado no storage, removendo job")
            self._remove_job(context.application, self._get_job_id(user_id, item_name))
            return

        old_price = item.last_price

        try:
            # Faz busca
            scraper = RagnatalesScraper()
            result = scraper.search_item(item_name)

            if result.ofertas:
                mais_barato = result.mais_barato()
                if mais_barato:
                    new_price = mais_barato.preco

                    # Verifica alertas configurados (antes de atualizar o preço)
                    alert_messages = item.check_alerts(new_price)
                    for alert_msg in alert_messages:
                        await context.bot.send_message(
                            chat_id=chat_id,
                            text=alert_msg,
                            parse_mode='Markdown'
                        )
                        logger.info(f"Alerta enviado para '{item_name}'")

                    # Verifica se preço mudou (notificação padrão)
                    if item.update_price(new_price):
                        # Salva atualização
                        self.storage.update(item)

                        # Envia notificação de mudança de preço
                        message = item.price_change_message(old_price, new_price)
                        await context.bot.send_message(
                            chat_id=chat_id,
                            text=message,
                            parse_mode='Markdown'
                        )
                        logger.info(f"Notificação enviada: {item_name} mudou de {old_price} para {new_price}")
                    else:
                        # Apenas atualiza timestamp e salva alertas disparados
                        self.storage.update(item)
                        logger.debug(f"Preço de '{item_name}' não mudou: {new_price}")

        except ItemNotFoundException:
            logger.warning(f"Item '{item_name}' não encontrado durante verificação")
        except ScraperException as e:
            logger.error(f"Erro ao verificar '{item_name}': {str(e)}")
        except Exception as e:
            logger.error(f"Erro inesperado ao verificar '{item_name}': {str(e)}")

    async def remove_monitor(
        self,
        application: Application,
        user_id: int,
        item_name: str
    ) -> tuple[bool, str]:
        """
        Remove item do monitoramento

        Returns:
            tuple: (sucesso, mensagem)
        """
        if self.storage.remove(user_id, item_name):
            job_id = self._get_job_id(user_id, item_name)
            self._remove_job(application, job_id)
            logger.info(f"Monitoramento removido: {item_name} do usuário {user_id}")
            return True, f"Monitoramento de '{item_name}' removido"

        return False, f"Item '{item_name}' não está sendo monitorado"

    async def update_monitor(
        self,
        application: Application,
        user_id: int,
        chat_id: int,
        item_name: str,
        interval_minutes: Optional[int] = None,
        alert_drop_percent: Optional[float] = None,
        alert_rise_percent: Optional[float] = None,
        alert_target_price: Optional[int] = None,
        clear_alerts: bool = False
    ) -> tuple[bool, str]:
        """
        Atualiza parâmetros de um item monitorado

        Args:
            application: Aplicação do Telegram
            user_id: ID do usuário
            chat_id: ID do chat para notificações
            item_name: Nome do item
            interval_minutes: Novo intervalo em minutos (opcional)
            alert_drop_percent: Novo alerta de queda (opcional)
            alert_rise_percent: Novo alerta de subida (opcional)
            alert_target_price: Novo alerta de preço alvo (opcional)
            clear_alerts: Se True, limpa alertas não especificados

        Returns:
            tuple: (sucesso, mensagem)
        """
        # Busca item existente
        item = self.storage.get(user_id, item_name)
        if not item:
            return False, f"Item '{item_name}' não está sendo monitorado"

        # Valida intervalo se fornecido
        if interval_minutes is not None:
            if interval_minutes < MIN_INTERVAL_MINUTES:
                return False, f"Intervalo mínimo é {MIN_INTERVAL_MINUTES} minutos"
            item.interval_minutes = interval_minutes

        # Atualiza alertas
        if clear_alerts:
            # Limpa todos e define apenas os novos
            item.alert_drop_percent = alert_drop_percent
            item.alert_rise_percent = alert_rise_percent
            item.alert_target_price = alert_target_price
            # Reseta flags de alertas disparados
            item.reset_alerts()
        else:
            # Atualiza apenas os fornecidos
            if alert_drop_percent is not None:
                item.alert_drop_percent = alert_drop_percent
                item.alert_drop_triggered = False
            if alert_rise_percent is not None:
                item.alert_rise_percent = alert_rise_percent
                item.alert_rise_triggered = False
            if alert_target_price is not None:
                item.alert_target_price = alert_target_price
                item.alert_target_triggered = False

        # Salva alterações
        self.storage.update(item)

        # Reagenda job com novo intervalo
        self._schedule_job(application, item, chat_id)

        logger.info(f"Monitoramento atualizado: {item_name} para usuário {user_id}")

        # Monta mensagem de resposta
        response = f"Monitoramento de '*{item_name}*' atualizado\n"
        response += f"⏱️ Intervalo: {item.interval_minutes} minutos\n"
        response += f"📍 Preço base: {item.base_price:,}z\n".replace(",", ".") if item.base_price else ""

        if item.has_alerts_configured():
            response += f"\n🔔 Alertas: {item.alerts_summary()}"
        else:
            response += "\n🔕 Sem alertas configurados"

        return True, response

    def list_monitors(self, user_id: int) -> list[MonitoredItem]:
        """Lista itens monitorados de um usuário"""
        return self.storage.get_user_items(user_id)

    def restore_jobs(self, application: Application) -> int:
        """
        Restaura jobs após reinício do bot

        Returns:
            int: Número de jobs restaurados
        """
        items = self.storage.get_all_active()
        count = 0

        for item in items:
            # Usa user_id como chat_id (assumindo chat privado)
            self._schedule_job(application, item, item.user_id)
            count += 1

        logger.info(f"Restaurados {count} jobs de monitoramento")
        return count
