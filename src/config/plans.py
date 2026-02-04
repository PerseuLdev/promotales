"""Configuracao de planos e features do PromoTales"""

from dataclasses import dataclass
from typing import List, Dict
from enum import Enum


class PlanType(Enum):
    """Tipos de plano disponiveis"""
    FREE = "free"
    BASIC = "basic"
    PREMIUM = "premium"


@dataclass
class PlanFeatures:
    """Features e limites de cada plano"""
    name: str
    price_monthly: float  # em BRL
    searches_per_day: int
    price_history_days: int  # 0 = sem acesso
    market_analysis: bool
    buy_sell_recommendation: bool
    price_alerts: bool  # Alertas de preco
    export_data: bool  # Exportar para CSV/Excel
    priority_support: bool


# Definicao dos planos
PLANS: Dict[PlanType, PlanFeatures] = {
    PlanType.FREE: PlanFeatures(
        name="Gratis",
        price_monthly=0.0,
        searches_per_day=10,
        price_history_days=0,  # Sem historico
        market_analysis=False,
        buy_sell_recommendation=False,
        price_alerts=False,
        export_data=False,
        priority_support=False
    ),
    PlanType.BASIC: PlanFeatures(
        name="Basico",
        price_monthly=9.90,
        searches_per_day=50,
        price_history_days=7,
        market_analysis=True,
        buy_sell_recommendation=False,
        price_alerts=False,
        export_data=False,
        priority_support=False
    ),
    PlanType.PREMIUM: PlanFeatures(
        name="Premium",
        price_monthly=19.90,
        searches_per_day=-1,  # Ilimitado
        price_history_days=30,
        market_analysis=True,
        buy_sell_recommendation=True,
        price_alerts=True,
        export_data=True,
        priority_support=True
    )
}


# Em ambiente de teste, todos tem acesso premium
TEST_MODE = True


def get_user_plan(user_id: int) -> PlanType:
    """
    Retorna o plano do usuario.
    Em modo teste, retorna PREMIUM para todos.
    """
    if TEST_MODE:
        return PlanType.PREMIUM

    # TODO: Implementar busca no banco de dados
    # Por enquanto retorna FREE
    return PlanType.FREE


def get_plan_features(user_id: int) -> PlanFeatures:
    """Retorna as features do plano do usuario"""
    plan_type = get_user_plan(user_id)
    return PLANS[plan_type]


def can_access_feature(user_id: int, feature: str) -> bool:
    """Verifica se usuario pode acessar uma feature"""
    features = get_plan_features(user_id)
    return getattr(features, feature, False)
