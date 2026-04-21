"""
Camada de negócio: implementa as seis análises do case NovaShop.
Cada função é pura (recebe DataFrames, retorna resultados), facilitando testes.
"""

from __future__ import annotations

import warnings
from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy import stats

from novashop.config import TOP_N_PRODUTOS, ALPHA_TESTE_T

warnings.filterwarnings("ignore", category=FutureWarning)


# ── Questão 1: Distribuição de pedidos por status ───────────────────────────

@dataclass
class ResultadoStatus:
    tabela: pd.DataFrame    # status | total | percentual


def analise_status_pedidos(pedidos: pd.DataFrame) -> ResultadoStatus:
    """Volume e participação percentual de cada status de pedido."""
    contagem = (
        pedidos["status"]
        .value_counts()
        .reset_index()
        .rename(columns={"count": "total"})
    )
    contagem["percentual"] = (contagem["total"] / contagem["total"].sum() * 100).round(2)
    contagem = contagem.sort_values("total", ascending=False).reset_index(drop=True)
    return ResultadoStatus(tabela=contagem)


# ── Questão 2: Top-N produtos mais vendidos ──────────────────────────────────

@dataclass
class ResultadoTopProdutos:
    tabela: pd.DataFrame    # produto | categoria | qtd_vendida | receita_total


def analise_top_produtos(
    itens: pd.DataFrame,
    produtos: pd.DataFrame,
    pedidos: pd.DataFrame,
    n: int = TOP_N_PRODUTOS,
) -> ResultadoTopProdutos:
    """
    Rank os N produtos com maior quantidade vendida em pedidos não-cancelados.
    Receita = soma de (preco_praticado × quantidade) já com desconto embutido.
    """
    pedidos_validos = pedidos[~pedidos["status"].isin(["cancelado"])]["id"]
    itens_validos = itens[itens["pedido_id"].isin(pedidos_validos)].copy()

    itens_validos["receita_item"] = (
        itens_validos["preco_praticado"]
        * itens_validos["quantidade"]
        * (1 - itens_validos["desconto_aplicado"])
    )

    agrupado = (
        itens_validos
        .groupby("produto_id")
        .agg(qtd_vendida=("quantidade", "sum"),
             receita_total=("receita_item", "sum"))
        .reset_index()
    )

    top = (
        agrupado
        .nlargest(n, "qtd_vendida")
        .merge(produtos[["id", "nome", "categoria"]], left_on="produto_id", right_on="id")
        .rename(columns={"nome": "produto", "id_y": "produto_id"})
        [["produto", "categoria", "qtd_vendida", "receita_total"]]
        .reset_index(drop=True)
    )
    top.index = top.index + 1  # ranking começa em 1
    return ResultadoTopProdutos(tabela=top)


# ── Questão 3: Ticket médio B2C vs B2B ──────────────────────────────────────

@dataclass
class ResultadoTicketMedio:
    tabela: pd.DataFrame        # segmento | n_pedidos | ticket_medio | desvio_padrao
    p_valor: float
    diferenca_significativa: bool
    teste_utilizado: str


def analise_ticket_medio(
    pedidos: pd.DataFrame,
    clientes: pd.DataFrame,
) -> ResultadoTicketMedio:
    """
    Calcula o ticket médio por segmento e aplica teste t de Welch
    para verificar significância estatística da diferença.
    """
    pedidos_seg = pedidos.merge(
        clientes[["id", "segmento"]], left_on="cliente_id", right_on="id"
    )
    pedidos_entregues = pedidos_seg[pedidos_seg["status"] == "entregue"]

    resumo = (
        pedidos_entregues
        .groupby("segmento")["valor_total"]
        .agg(n_pedidos="count", ticket_medio="mean", desvio_padrao="std")
        .reset_index()
    )
    resumo["ticket_medio"]  = resumo["ticket_medio"].round(2)
    resumo["desvio_padrao"] = resumo["desvio_padrao"].round(2)

    b2c = pedidos_entregues.loc[pedidos_entregues["segmento"] == "B2C", "valor_total"]
    b2b = pedidos_entregues.loc[pedidos_entregues["segmento"] == "B2B", "valor_total"]

    # Teste t de Welch — não assume variâncias iguais, adequado para amostras desbalanceadas
    _, p_valor = stats.ttest_ind(b2c, b2b, equal_var=False)

    return ResultadoTicketMedio(
        tabela=resumo,
        p_valor=round(p_valor, 6),
        diferenca_significativa=bool(p_valor < ALPHA_TESTE_T),
        teste_utilizado="Teste t de Welch (bicaudal, α=0.05)",
    )


# ── Questão 4: Evolução mensal de pedidos ───────────────────────────────────

@dataclass
class ResultadoEvolucao:
    tabela: pd.DataFrame        # ano_mes | total_pedidos | variacao_pct
    hipoteses: list[str]


def analise_evolucao_mensal(pedidos: pd.DataFrame) -> ResultadoEvolucao:
    """
    Agrega pedidos por mês e identifica picos e quedas relevantes (>20% de variação).
    As hipóteses são geradas programaticamente com base nos meses de calendário.
    """
    df = pedidos.copy()
    df["ano_mes"] = df["data_pedido"].dt.to_period("M")

    serie = (
        df.groupby("ano_mes")
        .size()
        .reset_index(name="total_pedidos")
        .sort_values("ano_mes")
    )
    serie["variacao_pct"] = serie["total_pedidos"].pct_change().mul(100).round(1)

    hipoteses = _gerar_hipoteses(serie)

    return ResultadoEvolucao(tabela=serie, hipoteses=hipoteses)


# Calendário comercial brasileiro — explica variações no e-commerce
_CONTEXTO_MENSAL = {
    1:  "Pós-festas: orçamentos comprometidos com gastos de dezembro reduzem demanda; promoções de liquidação podem atenuar a queda",
    2:  "Carnaval desloca atenção do consumo online; mês com menos dias úteis impacta volume de pedidos",
    3:  "Retomada do consumo pós-Carnaval; início do ano letivo aquece eletrônicos, esporte e material escolar",
    4:  "Semana Santa pode deslocar consumo pontualmente; mês sem grande gatilho sazonal consolidado no e-commerce",
    5:  "Dia das Mães — um dos maiores picos do varejo brasileiro, com forte demanda em cosméticos, moda e eletrônicos",
    6:  "Dia dos Namorados impulsiona presentes, perfumaria e eletrônicos de menor valor",
    7:  "Liquidações de inverno e aquecimento pré-Dia dos Pais sustentam volume acima da média",
    8:  "Dia dos Pais — segundo maior evento sazonal do varejo; pico em eletrônicos e esportes",
    9:  "Baixa sazonalidade — intervalo entre Dia dos Pais e aquecimento pré-Black Friday",
    10: "Antecipação ao Black Friday: consumidores pesquisam e adiantam compras; primeiras promoções chegam ao mercado",
    11: "Black Friday e Cyber Monday concentram o maior volume de compras online do ano",
    12: "Normalização pós-Black Friday; foco em presentes de Natal, mas volume já veio em novembro",
}

def _gerar_hipoteses(serie: pd.DataFrame) -> list[str]:
    """Cruza variações mensais com o calendário comercial para gerar hipóteses."""
    LIMIAR_VARIACAO = 20.0
    hipoteses = []

    for _, row in serie.iterrows():
        variacao = row["variacao_pct"]
        if pd.isna(variacao) or abs(variacao) < LIMIAR_VARIACAO:
            continue

        mes      = row["ano_mes"].month
        direcao  = "↑ Pico" if variacao > 0 else "↓ Queda"
        contexto = _CONTEXTO_MENSAL.get(mes, "Sem evento sazonal identificado")

        hipoteses.append(
            f"{direcao} em {row['ano_mes']} ({variacao:+.1f}%): {contexto}"
        )

    return hipoteses if hipoteses else ["Sem variações superiores a 20% detectadas."]


# ── Questão 5: Canal de aquisição × cancelamentos e ticket médio ─────────────

@dataclass
class ResultadoCanal:
    tabela: pd.DataFrame        # canal | total | cancelados | taxa_cancel | ticket_medio
    maior_cancelamento: str
    maior_ticket: str


def analise_canal_aquisicao(
    pedidos: pd.DataFrame,
    clientes: pd.DataFrame,
) -> ResultadoCanal:
    """
    Cruza clientes (canal de aquisição) com pedidos para calcular:
    - taxa de cancelamento por canal
    - ticket médio por canal
    """
    df = pedidos.merge(
        clientes[["id", "canal_aquisicao"]], left_on="cliente_id", right_on="id"
    )

    resumo = (
        df.groupby("canal_aquisicao")
        .agg(
            total=("id_x", "count"),
            cancelados=("status", lambda s: (s == "cancelado").sum()),
            ticket_medio=("valor_total", "mean"),
        )
        .reset_index()
    )
    resumo["taxa_cancelamento_pct"] = (
        resumo["cancelados"] / resumo["total"] * 100
    ).round(2)
    resumo["ticket_medio"] = resumo["ticket_medio"].round(2)
    resumo = resumo.sort_values("taxa_cancelamento_pct", ascending=False).reset_index(drop=True)

    return ResultadoCanal(
        tabela=resumo,
        maior_cancelamento=resumo.iloc[0]["canal_aquisicao"],
        maior_ticket=resumo.nlargest(1, "ticket_medio").iloc[0]["canal_aquisicao"],
    )
