"""Modelo de dados para historico de precos"""

import re
from dataclasses import dataclass, field
from typing import List, Optional
from datetime import datetime


@dataclass
class PriceHistoryEntry:
    """Uma entrada do historico de precos"""
    data: str  # Data formatada (ex: "30/01")
    data_completa: str  # Data completa (ex: "30 de jan. de 2026")
    quantidade: int
    preco_min: int
    preco_medio: int
    preco_max: int
    total_vendido: int
    refinamento: str = "Nao refinado"
    cartas: str = "Nenhuma"
    bonus: str = "Nenhum"

    @classmethod
    def from_row_text(cls, texto: str) -> Optional['PriceHistoryEntry']:
        """
        Cria uma entrada a partir do texto de uma linha da tabela.

        Formato esperado:
        30 de jan. de 2026
        Nao refinado
        Nenhuma carta equipada
        Nenhum bonus aleatorio
        13.810
        1.999
        1.999
        2.000
        27.606.686
        """
        try:
            linhas = [l.strip() for l in texto.strip().split('\n') if l.strip()]

            if len(linhas) < 9:
                return None

            # Extrai data
            data_completa = linhas[0]
            # Converte "30 de jan. de 2026" para "30/01"
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

            # Extrai valores numericos (remove pontos de milhar)
            def parse_num(s: str) -> int:
                return int(s.replace('.', '').replace(',', ''))

            return cls(
                data=data,
                data_completa=data_completa,
                refinamento=linhas[1] if len(linhas) > 1 else "Nao refinado",
                cartas=linhas[2] if len(linhas) > 2 else "Nenhuma",
                bonus=linhas[3] if len(linhas) > 3 else "Nenhum",
                quantidade=parse_num(linhas[4]) if len(linhas) > 4 else 0,
                preco_min=parse_num(linhas[5]) if len(linhas) > 5 else 0,
                preco_medio=parse_num(linhas[6]) if len(linhas) > 6 else 0,
                preco_max=parse_num(linhas[7]) if len(linhas) > 7 else 0,
                total_vendido=parse_num(linhas[8]) if len(linhas) > 8 else 0
            )
        except Exception:
            return None

    def preco_min_formatado(self) -> str:
        return f"{self.preco_min:,}".replace(",", ".")

    def preco_medio_formatado(self) -> str:
        return f"{self.preco_medio:,}".replace(",", ".")

    def preco_max_formatado(self) -> str:
        return f"{self.preco_max:,}".replace(",", ".")


@dataclass
class PriceHistory:
    """Historico completo de precos com analises"""
    item_nome: str
    entries: List[PriceHistoryEntry] = field(default_factory=list)

    def tendencia(self) -> str:
        """Calcula a tendencia de preco (subindo, descendo, estavel)"""
        if len(self.entries) < 2:
            return "indefinida"

        preco_atual = self.entries[0].preco_medio
        preco_antigo = self.entries[-1].preco_medio

        variacao = ((preco_atual - preco_antigo) / preco_antigo) * 100 if preco_antigo > 0 else 0

        if variacao > 5:
            return "subindo"
        elif variacao < -5:
            return "descendo"
        else:
            return "estavel"

    def variacao_percentual(self) -> float:
        """Calcula a variacao percentual no periodo"""
        if len(self.entries) < 2:
            return 0.0

        preco_atual = self.entries[0].preco_medio
        preco_antigo = self.entries[-1].preco_medio

        if preco_antigo == 0:
            return 0.0

        return ((preco_atual - preco_antigo) / preco_antigo) * 100

    def media_periodo(self) -> int:
        """Calcula a media de preco no periodo"""
        if not self.entries:
            return 0
        return sum(e.preco_medio for e in self.entries) // len(self.entries)

    def preco_min_periodo(self) -> int:
        """Menor preco do periodo"""
        if not self.entries:
            return 0
        return min(e.preco_min for e in self.entries)

    def preco_max_periodo(self) -> int:
        """Maior preco do periodo"""
        if not self.entries:
            return 0
        return max(e.preco_max for e in self.entries)

    def volatilidade(self) -> str:
        """Analisa a volatilidade do mercado"""
        if not self.entries:
            return "indefinida"

        preco_min = self.preco_min_periodo()
        preco_max = self.preco_max_periodo()

        if preco_min == 0:
            return "indefinida"

        variacao = ((preco_max - preco_min) / preco_min) * 100

        if variacao > 20:
            return "alta"
        elif variacao > 10:
            return "media"
        else:
            return "baixa"

    def recomendacao_compra(self, preco_atual: int) -> tuple[str, str]:
        """
        Analisa se e boa hora de comprar ou vender.

        Returns:
            Tuple (recomendacao, emoji)
        """
        media = self.media_periodo()

        if media == 0:
            return "Dados insuficientes", "⚪"

        diferenca_pct = ((preco_atual - media) / media) * 100

        if diferenca_pct < -5:
            return "BOA HORA PARA COMPRAR", "🟢"
        elif diferenca_pct > 5:
            return "BOA HORA PARA VENDER", "🔴"
        else:
            return "MERCADO ESTAVEL", "🟡"

    def oferta_status(self) -> str:
        """Analisa o nivel de oferta baseado na quantidade"""
        if not self.entries:
            return "indefinida"

        qtd_atual = self.entries[0].quantidade
        qtd_media = sum(e.quantidade for e in self.entries) // len(self.entries)

        if qtd_atual > qtd_media * 1.2:
            return "alta"
        elif qtd_atual < qtd_media * 0.8:
            return "baixa"
        else:
            return "normal"

    def to_analysis_message(self, preco_atual: int, dias: int = 7) -> str:
        """Gera mensagem de analise completa

        Args:
            preco_atual: Preco atual do item
            dias: Numero de dias para exibir no historico (7, 15, 30, 60)
        """
        # Filtra entries pelo periodo
        entries_periodo = self.entries[:dias]

        # Calcula metricas baseadas no periodo selecionado
        if len(entries_periodo) >= 2:
            preco_atual_periodo = entries_periodo[0].preco_medio
            preco_antigo = entries_periodo[-1].preco_medio
            variacao = ((preco_atual_periodo - preco_antigo) / preco_antigo) * 100 if preco_antigo > 0 else 0

            if variacao > 5:
                tendencia = "subindo"
            elif variacao < -5:
                tendencia = "descendo"
            else:
                tendencia = "estavel"
        else:
            tendencia = "indefinida"
            variacao = 0.0

        volatilidade = self.volatilidade()
        recomendacao, emoji_rec = self.recomendacao_compra(preco_atual)
        oferta = self.oferta_status()

        # Emojis de tendencia
        emoji_tend = "📈" if tendencia == "subindo" else "📉" if tendencia == "descendo" else "➡️"

        # Emoji de volatilidade
        emoji_vol = "⚡" if volatilidade == "alta" else "〰️" if volatilidade == "media" else "😴"

        # Emoji de oferta
        emoji_oferta = "📦" if oferta == "alta" else "📭" if oferta == "baixa" else "📫"

        msg = f"📊 *Analise de Mercado - {self.item_nome}*\n\n"

        msg += f"{emoji_tend} *Tendencia:* {tendencia.capitalize()} ({variacao:+.1f}%)\n"
        msg += f"{emoji_rec} *Recomendacao:* {recomendacao}\n"
        msg += f"{emoji_vol} *Volatilidade:* {volatilidade.capitalize()}\n"
        msg += f"{emoji_oferta} *Oferta:* {oferta.capitalize()}"

        if self.entries:
            msg += f" ({self.entries[0].quantidade:,} un)".replace(",", ".")

        msg += "\n\n"

        # Historico resumido (mostra quantos dias realmente disponiveis)
        dias_disponiveis = len(entries_periodo)
        if dias_disponiveis < dias:
            msg += f"📅 *Historico ({dias_disponiveis}/{dias} dias disponiveis):*\n"
        else:
            msg += f"📅 *Historico ({dias} dias):*\n"
        for i, entry in enumerate(entries_periodo):
            # Indicador de variacao dia a dia
            if i < len(entries_periodo) - 1:
                preco_atual_dia = entry.preco_medio
                preco_anterior = entries_periodo[i + 1].preco_medio
                if preco_atual_dia > preco_anterior:
                    emoji_dia = "📈"
                elif preco_atual_dia < preco_anterior:
                    emoji_dia = "📉"
                else:
                    emoji_dia = "➡️"
            else:
                emoji_dia = "➡️"

            msg += f"`{entry.data}` | Min: {entry.preco_min_formatado()} | Med: {entry.preco_medio_formatado()} | Max: {entry.preco_max_formatado()} {emoji_dia}\n"

        return msg.strip()
