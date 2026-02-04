"""Modelo para itens monitorados"""

from dataclasses import dataclass, field, asdict
from typing import Optional, List, Dict, Any
from datetime import datetime
import json


@dataclass
class MonitoredItem:
    """Representa um item sendo monitorado por um usuário"""

    user_id: int
    item_name: str
    interval_minutes: int
    last_price: Optional[int] = None
    last_search: Optional[str] = None
    created_at: Optional[str] = None
    active: bool = True
    # Alertas de preço
    base_price: Optional[int] = None  # Preço base para calcular porcentagens
    alert_drop_percent: Optional[float] = None  # Alerta quando cair X% (ex: 50 = -50%)
    alert_rise_percent: Optional[float] = None  # Alerta quando subir X% (ex: 30 = +30%)
    alert_target_price: Optional[int] = None  # Alerta quando chegar no valor X
    # Controle de alertas já disparados
    alert_drop_triggered: bool = False
    alert_rise_triggered: bool = False
    alert_target_triggered: bool = False

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        """Converte para dicionário"""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MonitoredItem':
        """Cria instância a partir de dicionário"""
        return cls(**data)

    def update_price(self, new_price: int) -> bool:
        """
        Atualiza o preço e retorna True se mudou

        Args:
            new_price: Novo preço encontrado

        Returns:
            bool: True se o preço mudou, False caso contrário
        """
        old_price = self.last_price
        self.last_price = new_price
        self.last_search = datetime.now().isoformat()

        if old_price is None:
            return False  # Primeira busca, não notifica

        return old_price != new_price

    def check_alerts(self, new_price: int) -> List[str]:
        """
        Verifica se algum alerta foi acionado

        Args:
            new_price: Novo preço encontrado

        Returns:
            List[str]: Lista de mensagens de alerta (pode ser vazia)
        """
        alerts = []

        if self.base_price is None or self.base_price == 0:
            return alerts

        # Calcula variação percentual em relação ao preço base
        percent_change = ((new_price - self.base_price) / self.base_price) * 100

        # Alerta de queda
        if self.alert_drop_percent is not None and not self.alert_drop_triggered:
            if percent_change <= -self.alert_drop_percent:
                self.alert_drop_triggered = True
                alerts.append(self._format_drop_alert(new_price, percent_change))

        # Alerta de subida
        if self.alert_rise_percent is not None and not self.alert_rise_triggered:
            if percent_change >= self.alert_rise_percent:
                self.alert_rise_triggered = True
                alerts.append(self._format_rise_alert(new_price, percent_change))

        # Alerta de preço alvo
        if self.alert_target_price is not None and not self.alert_target_triggered:
            if new_price <= self.alert_target_price:
                self.alert_target_triggered = True
                alerts.append(self._format_target_alert(new_price))

        return alerts

    def _format_drop_alert(self, new_price: int, percent_change: float) -> str:
        """Formata mensagem de alerta de queda"""
        return (
            f"🔔 *Alerta de Queda Atingido!*\n\n"
            f"Item: *{self.item_name}*\n"
            f"📉 Caiu *{abs(percent_change):.1f}%* do preço base!\n\n"
            f"Preço base: {self.base_price:,}z\n"
            f"Preço atual: {new_price:,}z\n"
            f"Meta: -{self.alert_drop_percent}%\n\n"
            f"@market {self.item_name}"
        ).replace(",", ".")

    def _format_rise_alert(self, new_price: int, percent_change: float) -> str:
        """Formata mensagem de alerta de subida"""
        return (
            f"🔔 *Alerta de Subida Atingido!*\n\n"
            f"Item: *{self.item_name}*\n"
            f"📈 Subiu *{percent_change:.1f}%* do preço base!\n\n"
            f"Preço base: {self.base_price:,}z\n"
            f"Preço atual: {new_price:,}z\n"
            f"Meta: +{self.alert_rise_percent}%\n\n"
            f"@market {self.item_name}"
        ).replace(",", ".")

    def _format_target_alert(self, new_price: int) -> str:
        """Formata mensagem de alerta de preço alvo"""
        return (
            f"🎯 *Preço Alvo Atingido!*\n\n"
            f"Item: *{self.item_name}*\n"
            f"O preço chegou em *{new_price:,}z*!\n\n"
            f"Preço base: {self.base_price:,}z\n"
            f"Meta: {self.alert_target_price:,}z\n\n"
            f"@market {self.item_name}"
        ).replace(",", ".")

    def reset_alerts(self) -> None:
        """Reseta os flags de alertas disparados (para permitir novos alertas)"""
        self.alert_drop_triggered = False
        self.alert_rise_triggered = False
        self.alert_target_triggered = False

    def has_alerts_configured(self) -> bool:
        """Verifica se tem algum alerta configurado"""
        return (
            self.alert_drop_percent is not None or
            self.alert_rise_percent is not None or
            self.alert_target_price is not None
        )

    def alerts_summary(self) -> str:
        """Retorna resumo dos alertas configurados"""
        parts = []
        if self.alert_drop_percent is not None:
            status = "✅" if self.alert_drop_triggered else "⏳"
            parts.append(f"{status} Queda -{self.alert_drop_percent}%")
        if self.alert_rise_percent is not None:
            status = "✅" if self.alert_rise_triggered else "⏳"
            parts.append(f"{status} Subida +{self.alert_rise_percent}%")
        if self.alert_target_price is not None:
            status = "✅" if self.alert_target_triggered else "⏳"
            parts.append(f"{status} Alvo {self.alert_target_price:,}z".replace(",", "."))
        return " | ".join(parts) if parts else "Sem alertas"

    def price_change_message(self, old_price: int, new_price: int) -> str:
        """
        Gera mensagem de mudança de preço

        Args:
            old_price: Preço anterior
            new_price: Novo preço

        Returns:
            str: Mensagem formatada
        """
        diff = new_price - old_price
        percent = (diff / old_price) * 100 if old_price > 0 else 0

        if diff < 0:
            emoji = "📉"
            direction = "caiu"
        else:
            emoji = "📈"
            direction = "subiu"

        return (
            f"{emoji} *Alerta de Preço!*\n\n"
            f"Item: *{self.item_name}*\n"
            f"Preço {direction}: {abs(diff):,}z ({abs(percent):.1f}%)\n"
            f"Anterior: {old_price:,}z\n"
            f"Atual: {new_price:,}z\n\n"
            f"@market {self.item_name}"
        ).replace(",", ".")


class MonitorStorage:
    """Gerencia persistência dos itens monitorados em JSON"""

    def __init__(self, filepath: str = "monitored_items.json"):
        self.filepath = filepath
        self._items: List[MonitoredItem] = []
        self.load()

    def load(self) -> None:
        """Carrega itens do arquivo JSON"""
        try:
            with open(self.filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self._items = [MonitoredItem.from_dict(item) for item in data]
        except FileNotFoundError:
            self._items = []
        except json.JSONDecodeError:
            self._items = []

    def save(self) -> None:
        """Salva itens no arquivo JSON"""
        with open(self.filepath, 'w', encoding='utf-8') as f:
            data = [item.to_dict() for item in self._items]
            json.dump(data, f, ensure_ascii=False, indent=2)

    def add(self, item: MonitoredItem) -> bool:
        """
        Adiciona item para monitoramento

        Returns:
            bool: True se adicionou, False se já existe
        """
        # Verifica se já existe
        existing = self.get(item.user_id, item.item_name)
        if existing:
            return False

        self._items.append(item)
        self.save()
        return True

    def remove(self, user_id: int, item_name: str) -> bool:
        """
        Remove item do monitoramento

        Returns:
            bool: True se removeu, False se não existia
        """
        item = self.get(user_id, item_name)
        if item:
            self._items.remove(item)
            self.save()
            return True
        return False

    def get(self, user_id: int, item_name: str) -> Optional[MonitoredItem]:
        """Busca item específico de um usuário"""
        for item in self._items:
            if item.user_id == user_id and item.item_name.lower() == item_name.lower():
                return item
        return None

    def get_user_items(self, user_id: int) -> List[MonitoredItem]:
        """Retorna todos os itens de um usuário"""
        return [item for item in self._items if item.user_id == user_id and item.active]

    def get_all_active(self) -> List[MonitoredItem]:
        """Retorna todos os itens ativos"""
        return [item for item in self._items if item.active]

    def update(self, item: MonitoredItem) -> None:
        """Atualiza item existente"""
        for i, existing in enumerate(self._items):
            if existing.user_id == item.user_id and existing.item_name.lower() == item.item_name.lower():
                self._items[i] = item
                self.save()
                return
