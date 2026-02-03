"""Modelo de dados para ofertas de itens no market"""

import re
from dataclasses import dataclass, field
from typing import List, Optional, TYPE_CHECKING, Any


@dataclass
class ItemOffer:
    """Representa uma oferta de item no market"""

    nome: str
    preco: int
    localizacao: str
    refinamento: int = 0
    cartas: List[str] = field(default_factory=list)
    bonus_aleatorios: List[str] = field(default_factory=list)
    vendedor: str = ""
    descricao_loja: str = ""
    quantidade: int = 1  # Para itens simples (nao-equipamentos)
    item_id: Optional[str] = None  # ID do item para gerar link

    @property
    def link(self) -> str:
        """Retorna o link do item no site"""
        if self.item_id:
            return f"https://ragnatales.com.br/db/items/{self.item_id}"
        return ""

    @property
    def is_equipamento(self) -> bool:
        """Verifica se e um equipamento (tem refinamento, cartas ou bonus)"""
        return self.refinamento > 0 or bool(self.cartas) or bool(self.bonus_aleatorios)

    @property
    def is_item_simples(self) -> bool:
        """Verifica se e um item simples (sem refinamento, cartas ou bonus)"""
        return not self.is_equipamento

    @classmethod
    def from_text(cls, texto: str) -> Optional['ItemOffer']:
        """
        Cria um ItemOffer a partir do texto de uma loja.
        Detecta automaticamente se e equipamento ou item simples.

        Args:
            texto: Texto completo da div da loja

        Returns:
            ItemOffer ou None se nao conseguir parsear
        """
        try:
            linhas = texto.strip().split('\n')
            if len(linhas) < 3:
                return None

            # Primeira linha: nome do item (pode ter refinamento)
            primeira_linha = linhas[0].strip()

            # Extrai ID do item
            id_match = re.search(r'\(id:\s*(\d+)\)', primeira_linha)
            item_id = id_match.group(1) if id_match else None

            # Extrai refinamento (+0, +7, +9, +10, etc)
            refino_match = re.match(r'^\+(\d+)', primeira_linha)
            refinamento = int(refino_match.group(1)) if refino_match else 0

            # Extrai nome do item (remove refinamento e id)
            nome = primeira_linha
            if refino_match:
                nome = primeira_linha[len(refino_match.group(0)):]
            nome = re.sub(r'\s*\(id:\s*\d+\)', '', nome).strip()

            # Detecta se e item simples baseado na estrutura
            # Item simples: Nome (id) -> Quantidade -> Preco -> Loja -> Vendedor -> Local
            # Equipamento: Nome (id) -> [Cartas] -> [Bonus] -> Preco -> Loja -> Vendedor -> Local
            is_simple = cls._detect_simple_item(linhas)

            if is_simple:
                return cls._parse_simple_item(linhas, nome, item_id)
            else:
                return cls._parse_equipment(linhas, nome, refinamento, item_id)

        except Exception:
            return None

    @classmethod
    def _detect_simple_item(cls, linhas: List[str]) -> bool:
        """
        Detecta se o texto representa um item simples (nao-equipamento).

        Item simples tem estrutura:
        - Linha 0: Nome (id: XXXX)
        - Linha 1: Quantidade (numero pequeno, geralmente < 10000)
        - Linha 2: Preco (numero grande)

        Equipamento tem:
        - Linha 0: +XNome [slots] (id: XXXX)
        - Pode ter "Cartas Equipadas:" ou "Bonus Aleatorios:"
        """
        # Se tem marcadores de equipamento, nao e simples
        texto_completo = '\n'.join(linhas)
        if "Cartas Equipadas:" in texto_completo or "Bônus Aleatórios:" in texto_completo:
            return False

        # Se primeira linha tem refinamento, e equipamento
        if re.match(r'^\+\d+', linhas[0].strip()):
            return False

        # Verifica estrutura: linha 1 e 2 devem ser numeros
        if len(linhas) >= 3:
            linha1 = linhas[1].strip().replace('.', '')
            linha2 = linhas[2].strip().replace('.', '')

            # Ambas devem ser numeros
            if linha1.isdigit() and linha2.isdigit():
                num1 = int(linha1)
                num2 = int(linha2)
                # Quantidade e geralmente menor que preco
                # E quantidade raramente passa de 10000
                if num1 < num2 and num1 <= 50000:
                    return True

        return False

    @classmethod
    def _parse_simple_item(cls, linhas: List[str], nome: str, item_id: Optional[str] = None) -> Optional['ItemOffer']:
        """
        Parseia um item simples (consumivel, ETC, municao, carta, pet).

        Estrutura esperada:
        - Linha 0: Nome (id: XXXX)
        - Linha 1: Quantidade
        - Linha 2: Preco
        - Linha 3: Nome da loja
        - Linha 4: Vendedor: XXX
        - Linha 5: Localizacao: @market X/Y
        """
        quantidade = 1
        preco = 0
        descricao_loja = ""
        vendedor = ""
        localizacao = ""

        for i, linha in enumerate(linhas[1:], start=1):
            linha = linha.strip()

            # Linha 1: Quantidade
            if i == 1 and linha.replace('.', '').isdigit():
                quantidade = int(linha.replace('.', ''))
                continue

            # Linha 2: Preco
            if i == 2 and linha.replace('.', '').isdigit():
                preco = int(linha.replace('.', ''))
                continue

            # Vendedor
            if linha.startswith("Vendedor:"):
                vendedor = linha.replace("Vendedor:", "").strip()
                continue

            # Localizacao
            if "Localização:" in linha or "@market" in linha:
                loc_match = re.search(r'@market\s*(\d+/\d+)', linha)
                if loc_match:
                    localizacao = f"@market {loc_match.group(1)}"
                continue

            # Nome da loja (linha entre preco e vendedor)
            if not descricao_loja and not linha.replace('.', '').isdigit():
                if not linha.startswith("Vendedor:") and "@market" not in linha:
                    descricao_loja = linha

        if not preco or not localizacao:
            return None

        return cls(
            nome=nome,
            preco=preco,
            localizacao=localizacao,
            refinamento=0,
            cartas=[],
            bonus_aleatorios=[],
            vendedor=vendedor,
            descricao_loja=descricao_loja,
            quantidade=quantidade,
            item_id=item_id
        )

    @classmethod
    def _parse_equipment(cls, linhas: List[str], nome: str, refinamento: int, item_id: Optional[str] = None) -> Optional['ItemOffer']:
        """
        Parseia um equipamento (arma, armadura, acessorio).

        Estrutura esperada:
        - Linha 0: +XNome [slots] (id: XXXX)
        - Cartas Equipadas: (opcional)
        - Bonus Aleatorios: (opcional)
        - Preco
        - Nome da loja
        - Vendedor: XXX
        - Localizacao: @market X/Y
        """
        cartas = []
        bonus_aleatorios = []
        preco = 0
        vendedor = ""
        localizacao = ""
        descricao_loja = ""

        modo = None  # 'cartas', 'bonus', None

        for linha in linhas[1:]:
            linha = linha.strip()

            if linha == "Cartas Equipadas:":
                modo = 'cartas'
                continue
            elif "Bônus Aleatórios:" in linha or "Bonus Aleatorios:" in linha:
                modo = 'bonus'
                continue
            elif linha.startswith("Vendedor:"):
                vendedor = linha.replace("Vendedor:", "").strip()
                modo = None
                continue
            elif linha.startswith("Localização:") or "@market" in linha:
                loc_match = re.search(r'@market\s*(\d+/\d+)', linha)
                if loc_match:
                    localizacao = f"@market {loc_match.group(1)}"
                modo = None
                continue

            # Tenta identificar preco (numero grande sem texto)
            if re.match(r'^[\d.]+$', linha) and len(linha) >= 5:
                preco_num = int(linha.replace('.', ''))
                if preco_num > preco:
                    preco = preco_num
                continue

            # Processa conforme o modo
            if modo == 'cartas' and linha:
                # Ignora linhas que sao apenas numeros ou "Item Icon"
                if linha.isdigit() or linha == "Item Icon":
                    continue
                carta = re.sub(r'\s*\(id:\s*\d+\)', '', linha).strip()
                if carta and not carta.isdigit() and carta != "Item Icon":
                    cartas.append(carta)
            elif modo == 'bonus' and linha:
                # Aceita bonus que contenham +X, -X, X% ou palavras-chave
                is_bonus = (
                    re.search(r'[+\-]\d+%?', linha) or  # Contem +X ou -X ou X%
                    'Ignora' in linha or
                    'Reduz' in linha or
                    'Recupera' in linha or
                    'Aumenta' in linha or
                    'Resist' in linha or
                    '%' in linha
                )
                if is_bonus:
                    bonus_aleatorios.append(linha)
                elif linha.isdigit() or linha == "Item Icon":
                    continue
                else:
                    # Fim dos bonus, provavelmente e descricao da loja
                    modo = None
                    if not descricao_loja and not linha.isdigit():
                        descricao_loja = linha
            elif modo is None and linha and not linha.isdigit():
                if not descricao_loja and linha not in ['1', '2', '3'] and linha != "Item Icon":
                    descricao_loja = linha

        if not preco or not localizacao:
            return None

        return cls(
            nome=nome,
            preco=preco,
            localizacao=localizacao,
            refinamento=refinamento,
            cartas=cartas,
            bonus_aleatorios=bonus_aleatorios,
            vendedor=vendedor,
            descricao_loja=descricao_loja,
            quantidade=1,
            item_id=item_id
        )

    def preco_formatado(self) -> str:
        """Retorna o preco formatado com pontos"""
        return f"{self.preco:,}".replace(",", ".")

    def nome_completo(self) -> str:
        """Retorna o nome com refinamento"""
        if self.refinamento > 0:
            return f"+{self.refinamento} {self.nome}"
        return self.nome

    def to_message(self, mostrar_detalhes: bool = True) -> str:
        """
        Formata a oferta para mensagem do Telegram

        Args:
            mostrar_detalhes: Se deve mostrar cartas e bonus

        Returns:
            Mensagem formatada
        """
        # Nome do item
        msg = f"🛒 *{self.nome_completo()}*\n\n"

        # Preco em destaque
        msg += f"💰 *Preco:* {self.preco_formatado()} zenys\n"

        # Quantidade para itens simples
        if self.quantidade > 1:
            msg += f"📦 *Quantidade:* {self.quantidade} un\n"

        # Localizacao
        msg += f"\n📍 *Local:* `{self.localizacao}`\n"

        # Vendedor
        if self.vendedor:
            msg += f"🏪 *Vendedor:* {self.vendedor}\n"

        # Cartas e bonus (com quebra de linha antes)
        if mostrar_detalhes and (self.cartas or self.bonus_aleatorios):
            msg += "\n"
            if self.cartas:
                msg += f"💎 *Cartas:* {', '.join(self.cartas)}\n"

            if self.bonus_aleatorios:
                # Mostra todos os bonus, um por linha se tiver mais de 2
                if len(self.bonus_aleatorios) <= 2:
                    bonus_str = ', '.join(self.bonus_aleatorios)
                    msg += f"✨ *Bonus:* {bonus_str}\n"
                else:
                    msg += f"✨ *Bonus:*\n"
                    for bonus in self.bonus_aleatorios:
                        msg += f"   • {bonus}\n"

        # Link do item
        if self.link:
            msg += f"\n🔗 [Ver no site]({self.link})"

        return msg.strip()


@dataclass
class ItemSearchResult:
    """Resultado completo de uma busca de item"""

    item_nome: str
    ofertas: List[ItemOffer] = field(default_factory=list)
    preco_medio: Optional[str] = None
    volume_vendas: Optional[str] = None  # Volume de vendas nos ultimos 45 dias
    price_history: Optional[Any] = None  # PriceHistory - historico de precos

    def is_equipamento(self) -> bool:
        """Verifica se as ofertas sao de equipamentos"""
        if not self.ofertas:
            return False
        # Se qualquer oferta tem refinamento, cartas ou bonus, e equipamento
        return any(o.is_equipamento for o in self.ofertas)

    def is_item_simples(self) -> bool:
        """Verifica se as ofertas sao de itens simples"""
        return not self.is_equipamento()

    def quantidade_total(self) -> int:
        """Retorna quantidade total disponivel (soma de todas as ofertas)"""
        return sum(o.quantidade for o in self.ofertas)

    def mais_barato(self, refinamento: Optional[int] = None) -> Optional[ItemOffer]:
        """
        Retorna a oferta mais barata

        Args:
            refinamento: Filtrar por refinamento especifico (None = qualquer)

        Returns:
            ItemOffer mais barato ou None
        """
        ofertas_filtradas = self.ofertas

        if refinamento is not None:
            ofertas_filtradas = [o for o in self.ofertas if o.refinamento == refinamento]

        if not ofertas_filtradas:
            return None

        return min(ofertas_filtradas, key=lambda x: x.preco)

    def mais_barato_por_faixa(self, faixa: str) -> Optional[ItemOffer]:
        """
        Retorna a oferta mais barata por faixa de refinamento

        Args:
            faixa: '0', '4-6', '7-9', '10+'

        Returns:
            ItemOffer mais barato na faixa ou None
        """
        if faixa == '0':
            return self.mais_barato(0)
        elif faixa == '4-6':
            ofertas = [o for o in self.ofertas if 4 <= o.refinamento <= 6]
        elif faixa == '7-9':
            ofertas = [o for o in self.ofertas if 7 <= o.refinamento <= 9]
        elif faixa == '10+':
            ofertas = [o for o in self.ofertas if o.refinamento >= 10]
        else:
            return self.mais_barato()

        if not ofertas:
            return None

        return min(ofertas, key=lambda x: x.preco)

    def refinamentos_disponiveis(self) -> List[int]:
        """Retorna lista de refinamentos disponiveis"""
        return sorted(set(o.refinamento for o in self.ofertas))

    def resumo(self) -> str:
        """Retorna um resumo da busca"""
        if not self.ofertas:
            return f"❌ '{self.item_nome}' nao encontrado no market"

        msg = f"🔍 {self.item_nome}\n"
        msg += f"📦 {len(self.ofertas)} ofertas encontradas\n\n"

        # Mais barato geral
        mais_barato = self.mais_barato()
        if mais_barato:
            msg += f"💰 Mais barato: {mais_barato.preco_formatado()}z"
            if mais_barato.refinamento > 0:
                msg += f" (+{mais_barato.refinamento})"
            msg += f"\n📍 {mais_barato.localizacao}\n"

            # Mostra quantidade para itens simples
            if mais_barato.quantidade > 1:
                msg += f"📦 Qtd nesta loja: {mais_barato.quantidade} un\n"

        # Quantidade total disponivel (para itens simples)
        if self.is_item_simples():
            total = self.quantidade_total()
            if total > 1:
                msg += f"🏪 Total no market: {total:,} un\n".replace(",", ".")

        # Volume de vendas
        if self.volume_vendas:
            msg += f"📈 Vendas 45d: {self.volume_vendas}"

        return msg.strip()
