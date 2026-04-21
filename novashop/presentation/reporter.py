"""
Camada de apresentação: geração de gráficos e impressão de resultados formatados.
Separa completamente a lógica de exibição das análises de negócio.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import pandas as pd

from novashop.config import CORES, ESTILO_GRAFICO, OUTPUT_DIR
from novashop.analysis.queries import (
    ResultadoStatus,
    ResultadoTopProdutos,
    ResultadoTicketMedio,
    ResultadoEvolucao,
    ResultadoCanal,
)
from novashop.data.loader import RelatorioLimpeza


# ── Helpers de formatação ────────────────────────────────────────────────────

def _fmt_reais(valor: float) -> str:
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _separador(titulo: str) -> None:
    largura = 70
    print("\n" + "═" * largura)
    print(f"  {titulo}")
    print("═" * largura)


def _salvar_figura(fig: plt.Figure, nome: str) -> Path:
    caminho = OUTPUT_DIR / nome
    fig.savefig(caminho, dpi=ESTILO_GRAFICO["dpi"], bbox_inches="tight")
    plt.close(fig)
    return caminho


# ── Questão 1 ────────────────────────────────────────────────────────────────

def exibir_status(res: ResultadoStatus) -> None:
    _separador("Q1 · Volume de Pedidos por Status")

    df = res.tabela.copy()
    df["percentual"] = df["percentual"].map(lambda x: f"{x:.2f}%")
    print(df.to_string(index=False))

    _plotar_status(res)


def _plotar_status(res: ResultadoStatus) -> None:
    df = res.tabela
    cores = [CORES["status"].get(s, CORES["neutro"]) for s in df["status"]]

    fig, (ax_bar, ax_pie) = plt.subplots(1, 2, figsize=(13, 5))
    fig.suptitle("Distribuição de Pedidos por Status", fontsize=ESTILO_GRAFICO["fonte_titulo"], fontweight="bold")

    # Barras
    bars = ax_bar.bar(df["status"], df["total"], color=cores, edgecolor="white", linewidth=0.8)
    ax_bar.set_title("Volume absoluto", fontsize=ESTILO_GRAFICO["fonte_eixo"])
    ax_bar.set_ylabel("Nº de Pedidos")
    ax_bar.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{int(x):,}"))
    for bar, pct in zip(bars, df["percentual"]):
        ax_bar.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 50,
                    f"{pct:.1f}%", ha="center", va="bottom", fontsize=9, fontweight="bold")

    # Pizza
    ax_pie.pie(df["total"], labels=df["status"], colors=cores,
               autopct="%1.1f%%", startangle=140,
               wedgeprops={"edgecolor": "white", "linewidth": 1.2})
    ax_pie.set_title("Participação percentual", fontsize=ESTILO_GRAFICO["fonte_eixo"])

    fig.tight_layout()
    caminho = _salvar_figura(fig, "q1_status_pedidos.png")
    print(f"\n  → Gráfico salvo em: {caminho}")


# ── Questão 2 ────────────────────────────────────────────────────────────────

def exibir_top_produtos(res: ResultadoTopProdutos) -> None:
    _separador("Q2 · Top 10 Produtos Mais Vendidos")

    df = res.tabela.copy()
    df["receita_total"] = df["receita_total"].map(_fmt_reais)
    df["qtd_vendida"]   = df["qtd_vendida"].map(lambda x: f"{x:,}")
    print(df.to_string())

    _plotar_top_produtos(res)


def _plotar_top_produtos(res: ResultadoTopProdutos) -> None:
    df = res.tabela.copy().sort_values("qtd_vendida")  # ascending p/ barh
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
    fig.suptitle("Top 10 Produtos — Quantidade Vendida e Receita",
                 fontsize=ESTILO_GRAFICO["fonte_titulo"], fontweight="bold")

    # Quantidade
    ax1.barh(df["produto"].str[:25], df["qtd_vendida"],
             color=CORES["primaria"], edgecolor="white")
    ax1.set_title("Quantidade vendida", fontsize=ESTILO_GRAFICO["fonte_eixo"])
    ax1.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{int(x):,}"))

    # Receita
    ax2.barh(df["produto"].str[:25], df["receita_total"] / 1_000,
             color=CORES["acento"], edgecolor="white")
    ax2.set_title("Receita total (R$ mil)", fontsize=ESTILO_GRAFICO["fonte_eixo"])
    ax2.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"R$ {x:,.0f}k"))

    for ax in (ax1, ax2):
        ax.tick_params(axis="y", labelsize=8)

    fig.tight_layout()
    caminho = _salvar_figura(fig, "q2_top_produtos.png")
    print(f"\n  → Gráfico salvo em: {caminho}")


# ── Questão 3 ────────────────────────────────────────────────────────────────

def exibir_ticket_medio(res: ResultadoTicketMedio) -> None:
    _separador("Q3 · Ticket Médio por Segmento (B2C vs B2B)")

    df = res.tabela.copy()
    df["ticket_medio"]  = df["ticket_medio"].map(_fmt_reais)
    df["desvio_padrao"] = df["desvio_padrao"].map(_fmt_reais)
    print(df.to_string(index=False))

    sig = "✔ SIM" if res.diferenca_significativa else "✘ NÃO"
    print(f"\n  Teste: {res.teste_utilizado}")
    print(f"  p-valor: {res.p_valor:.6f}")
    print(f"  Diferença estatisticamente significativa? {sig}  (α = 0.05)")

    _plotar_ticket_medio(res)


def _plotar_ticket_medio(res: ResultadoTicketMedio) -> None:
    df = res.tabela
    cores = [CORES["b2c"] if s == "B2C" else CORES["b2b"] for s in df["segmento"]]

    fig, ax = plt.subplots(figsize=ESTILO_GRAFICO["figura_tamanho"])
    bars = ax.bar(df["segmento"], df["ticket_medio"], color=cores,
                  edgecolor="white", linewidth=0.8, width=0.4)
    ax.set_title("Ticket Médio por Segmento de Cliente",
                 fontsize=ESTILO_GRAFICO["fonte_titulo"], fontweight="bold")
    ax.set_ylabel("Ticket Médio (R$)")
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"R$ {x:,.0f}"))

    for bar, row in zip(bars, df.itertuples()):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 20,
                _fmt_reais(row.ticket_medio), ha="center", va="bottom",
                fontsize=10, fontweight="bold")

    sig_txt = f"p = {res.p_valor:.4f} — {'Diferença significativa' if res.diferenca_significativa else 'Sem diferença significativa'}"
    ax.set_xlabel(sig_txt, labelpad=10)
    fig.tight_layout()
    caminho = _salvar_figura(fig, "q3_ticket_medio.png")
    print(f"\n  → Gráfico salvo em: {caminho}")


# ── Questão 4 ────────────────────────────────────────────────────────────────

def exibir_evolucao_mensal(res: ResultadoEvolucao) -> None:
    _separador("Q4 · Evolução Mensal de Pedidos (2023–2024)")

    df = res.tabela.copy()
    df["variacao_pct"] = df["variacao_pct"].map(
        lambda x: f"{x:+.1f}%" if pd.notna(x) else "—"
    )
    print(df.to_string(index=False))

    print("\n  Hipóteses para variações relevantes (>20%):")
    for h in res.hipoteses:
        print(f"    • {h}")

    _plotar_evolucao(res)


def _plotar_evolucao(res: ResultadoEvolucao) -> None:
    df = res.tabela.copy()
    rotulos = [str(p) for p in df["ano_mes"]]
    x = range(len(rotulos))

    fig, ax = plt.subplots(figsize=(13, 5))
    ax.plot(x, df["total_pedidos"], marker="o", linewidth=2.2,
            color=CORES["primaria"], zorder=3)
    ax.fill_between(x, df["total_pedidos"], alpha=0.12, color=CORES["primaria"])

    # Destaque de pico e vale
    idx_max = df["total_pedidos"].idxmax()
    idx_min = df["total_pedidos"].idxmin()
    for idx, cor, label in [(idx_max, CORES["sucesso"], "Pico"),
                             (idx_min, CORES["alerta"], "Mínimo")]:
        ax.scatter(idx, df.loc[idx, "total_pedidos"], color=cor, s=120, zorder=4)
        ax.annotate(f"{label}\n{df.loc[idx,'total_pedidos']:,}",
                    (idx, df.loc[idx, "total_pedidos"]),
                    textcoords="offset points", xytext=(0, 12),
                    ha="center", fontsize=8, color=cor, fontweight="bold")

    ax.set_title("Evolução Mensal do Volume de Pedidos",
                 fontsize=ESTILO_GRAFICO["fonte_titulo"], fontweight="bold")
    ax.set_xticks(list(x))
    ax.set_xticklabels(rotulos, rotation=45, ha="right", fontsize=8)
    ax.set_ylabel("Nº de Pedidos")
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"{int(v):,}"))
    ax.grid(axis="y", linestyle="--", alpha=0.4)

    fig.tight_layout()
    caminho = _salvar_figura(fig, "q4_evolucao_mensal.png")
    print(f"\n  → Gráfico salvo em: {caminho}")


# ── Questão 5 ────────────────────────────────────────────────────────────────

def exibir_canal(res: ResultadoCanal) -> None:
    _separador("Q5 · Canal de Aquisição × Cancelamentos e Ticket Médio")

    df = res.tabela.copy()
    df["ticket_medio"]         = df["ticket_medio"].map(_fmt_reais)
    df["taxa_cancelamento_pct"] = df["taxa_cancelamento_pct"].map(lambda x: f"{x:.2f}%")
    print(df[["canal_aquisicao", "total", "cancelados",
              "taxa_cancelamento_pct", "ticket_medio"]].to_string(index=False))

    print(f"\n  Canal com MAIOR taxa de cancelamento : {res.maior_cancelamento}")
    print(f"  Canal com MAIOR ticket médio         : {res.maior_ticket}")

    _plotar_canal(res)


def _plotar_canal(res: ResultadoCanal) -> None:
    df = res.tabela.copy()
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5))
    fig.suptitle("Canal de Aquisição: Cancelamentos vs Ticket Médio",
                 fontsize=ESTILO_GRAFICO["fonte_titulo"], fontweight="bold")

    ax1.bar(df["canal_aquisicao"], df["taxa_cancelamento_pct"],
            color=CORES["alerta"], edgecolor="white")
    ax1.set_title("Taxa de Cancelamento (%)")
    ax1.set_ylabel("%")
    for i, (_, row) in enumerate(df.iterrows()):
        ax1.text(i, row["taxa_cancelamento_pct"] + 0.2,
                 f"{row['taxa_cancelamento_pct']:.2f}%", ha="center", fontsize=9)

    ax2.bar(df["canal_aquisicao"], df["ticket_medio"],
            color=CORES["secundaria"], edgecolor="white")
    ax2.set_title("Ticket Médio (R$)")
    ax2.set_ylabel("R$")
    ax2.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"R$ {x:,.0f}"))

    fig.tight_layout()
    caminho = _salvar_figura(fig, "q5_canal_aquisicao.png")
    print(f"\n  → Gráfico salvo em: {caminho}")


# ── Questão 6 ────────────────────────────────────────────────────────────────

def exibir_limpeza(relatorio: RelatorioLimpeza) -> None:
    _separador("Q6 · Inconsistências Identificadas e Tratamentos Aplicados")

    df = relatorio.to_dataframe()
    if df.empty:
        print("  Nenhuma inconsistência detectada.")
        return

    for _, row in df.iterrows():
        print(f"\n  [{row['tabela']}] campo: {row['campo']}")
        print(f"    Problema   : {row['problema']}")
        print(f"    Ocorrências: {row['quantidade']:,}")
        print(f"    Ação       : {row['acao']}")

    caminho = OUTPUT_DIR / "q6_relatorio_limpeza.csv"
    df.to_csv(caminho, index=False)
    print(f"\n  → Relatório completo salvo em: {caminho}")
