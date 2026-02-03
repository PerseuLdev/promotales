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
            f"Atual: {new_price:,}z"
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
