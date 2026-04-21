"""
NovaShop Analytics — Ponto de entrada principal.
Orquestra o pipeline: carga → limpeza → análise → apresentação.
"""

import logging
import sys
import time

from novashop.data.loader import load_all, clean_dataset
from novashop.analysis.queries import (
    analise_status_pedidos,
    analise_top_produtos,
    analise_ticket_medio,
    analise_evolucao_mensal,
    analise_canal_aquisicao,
)
from novashop.presentation.reporter import (
    exibir_status,
    exibir_top_produtos,
    exibir_ticket_medio,
    exibir_evolucao_mensal,
    exibir_canal,
    exibir_limpeza,
)
from novashop.config import OUTPUT_DIR, TOP_N_PRODUTOS

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger("novashop.main")


def run() -> None:
    inicio = time.perf_counter()

    print("\n" + "▓" * 70)
    print("  NovaShop Analytics  —  Case Digital Peers Group")
    print("▓" * 70)

    # ── 1. Carga ──────────────────────────────────────────────────────────────
    logger.info("Carregando datasets…")
    try:
        ds = load_all()
    except FileNotFoundError as exc:
        logger.error("Falha ao carregar dados: %s", exc)
        sys.exit(1)

    # ── 2. Limpeza (Q6) ──────────────────────────────────────────────────────
    logger.info("Aplicando limpeza e documentando inconsistências…")
    ds, relatorio_limpeza = clean_dataset(ds)

    # ── 3. Análises ──────────────────────────────────────────────────────────
    logger.info("Executando análises…")

    res_status  = analise_status_pedidos(ds.pedidos)
    res_top     = analise_top_produtos(ds.itens_pedido, ds.produtos, ds.pedidos, TOP_N_PRODUTOS)
    res_ticket  = analise_ticket_medio(ds.pedidos, ds.clientes)
    res_evolucao= analise_evolucao_mensal(ds.pedidos)
    res_canal   = analise_canal_aquisicao(ds.pedidos, ds.clientes)

    # ── 4. Apresentação ──────────────────────────────────────────────────────
    logger.info("Gerando outputs…")

    exibir_status(res_status)
    exibir_top_produtos(res_top)
    exibir_ticket_medio(res_ticket)
    exibir_evolucao_mensal(res_evolucao)
    exibir_canal(res_canal)
    exibir_limpeza(relatorio_limpeza)

    # ── Sumário final ─────────────────────────────────────────────────────────
    elapsed = time.perf_counter() - inicio
    print("\n" + "═" * 70)
    print(f"  ✔  Análise concluída em {elapsed:.1f}s")
    print(f"  ✔  Gráficos e relatórios salvos em: {OUTPUT_DIR.resolve()}")
    print("═" * 70 + "\n")


if __name__ == "__main__":
    run()
