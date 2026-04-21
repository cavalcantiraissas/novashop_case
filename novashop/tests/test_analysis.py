"""
Testes unitários para as funções de análise do case NovaShop.
Execute com:  python -m pytest tests/ -v
"""

import pandas as pd
import pytest

from novashop.analysis.queries import (
    analise_status_pedidos,
    analise_top_produtos,
    analise_ticket_medio,
    analise_evolucao_mensal,
    analise_canal_aquisicao,
)
from novashop.data.loader import (
    clean_dataset,
    Dataset,
    RelatorioLimpeza,
    _clean_pedidos,
    _clean_itens_pedido,
)


# ── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture
def pedidos_simples() -> pd.DataFrame:
    """
    Fixture com dados suficientes para o teste t de Welch:
    mínimo de 2 pedidos entregues por segmento para evitar NaN no desvio-padrão.
    """
    return pd.DataFrame({
        "id":          [1, 2, 3, 4, 5, 6, 7],
        "cliente_id":  [1, 2, 1, 3, 2, 2, 3],
        "data_pedido": pd.to_datetime([
            "2023-01-10", "2023-11-20", "2024-05-01",
            "2024-12-15", "2023-06-30", "2023-08-01", "2024-02-10",
        ]),
        "status":      ["entregue", "cancelado", "entregue",
                        "entregue", "entregue",  "entregue",  "entregue"],
        "valor_total": [500.0, 200.0, 1500.0, 300.0, 800.0, 950.0, 420.0],
        "canal_venda": ["site", "app", "site", "marketplace", "app", "site", "app"],
        "cupom_desconto": ["não", "sim", "não", "não", "sim", "não", "sim"],
    })


@pytest.fixture
def clientes_simples() -> pd.DataFrame:
    return pd.DataFrame({
        "id":              [1, 2, 3],
        "segmento":        ["B2C", "B2B", "B2B"],   # 2 B2B para suportar o teste t
        "canal_aquisicao": ["orgânico", "paid_search", "redes_sociais"],
    })


@pytest.fixture
def produtos_simples() -> pd.DataFrame:
    return pd.DataFrame({
        "id":        [10, 20, 30],
        "nome":      ["Produto A", "Produto B", "Produto C"],
        "categoria": ["Eletrônicos", "Casa", "Moda"],
    })


@pytest.fixture
def itens_simples() -> pd.DataFrame:
    return pd.DataFrame({
        "id":               [1, 2, 3, 4],
        "pedido_id":        [1, 3, 5, 2],     # pedido 2 = cancelado
        "produto_id":       [10, 10, 20, 30],
        "quantidade":       [2, 3, 1, 5],
        "preco_praticado":  [100.0, 100.0, 200.0, 50.0],
        "desconto_aplicado":[0.1, 0.0, 0.2, 0.0],
    })


# ── Q1 ────────────────────────────────────────────────────────────────────────

class TestAnaliseStatus:
    def test_contagem_correta(self, pedidos_simples):
        res = analise_status_pedidos(pedidos_simples)
        totais = res.tabela.set_index("status")["total"].to_dict()
        assert totais["entregue"] == 6
        assert totais["cancelado"] == 1
        assert "devolvido" not in totais

    def test_soma_percentual_100(self, pedidos_simples):
        res = analise_status_pedidos(pedidos_simples)
        assert abs(res.tabela["percentual"].sum() - 100.0) < 0.01

    def test_ordenado_descendente(self, pedidos_simples):
        res = analise_status_pedidos(pedidos_simples)
        totais = res.tabela["total"].tolist()
        assert totais == sorted(totais, reverse=True)


# ── Q2 ────────────────────────────────────────────────────────────────────────

class TestTopProdutos:
    def test_exclui_cancelados(self, itens_simples, produtos_simples, pedidos_simples):
        res = analise_top_produtos(itens_simples, produtos_simples, pedidos_simples, n=3)
        # Produto C (pedido 2, cancelado) não deve aparecer na receita significativa
        produtos_resultado = res.tabela["produto"].tolist()
        assert "Produto C" not in produtos_resultado

    def test_respeita_n(self, itens_simples, produtos_simples, pedidos_simples):
        res = analise_top_produtos(itens_simples, produtos_simples, pedidos_simples, n=2)
        assert len(res.tabela) <= 2

    def test_produto_mais_vendido_primeiro(self, itens_simples, produtos_simples, pedidos_simples):
        res = analise_top_produtos(itens_simples, produtos_simples, pedidos_simples, n=3)
        # Produto A: qtd 5 (pedidos 1+3), Produto B: qtd 1
        assert res.tabela.iloc[0]["produto"] == "Produto A"


# ── Q3 ────────────────────────────────────────────────────────────────────────

class TestTicketMedio:
    def test_segmentos_presentes(self, pedidos_simples, clientes_simples):
        res = analise_ticket_medio(pedidos_simples, clientes_simples)
        segmentos = set(res.tabela["segmento"])
        assert {"B2C", "B2B"}.issubset(segmentos)

    def test_p_valor_entre_0_e_1(self, pedidos_simples, clientes_simples):
        import math
        res = analise_ticket_medio(pedidos_simples, clientes_simples)
        assert not math.isnan(res.p_valor), "p-valor NaN: amostra insuficiente (<2 obs/grupo)"
        assert 0.0 <= res.p_valor <= 1.0

    def test_flag_significancia_coerente(self, pedidos_simples, clientes_simples):
        res = analise_ticket_medio(pedidos_simples, clientes_simples)
        esperado = res.p_valor < 0.05
        assert res.diferenca_significativa == esperado


# ── Q4 ────────────────────────────────────────────────────────────────────────

class TestEvolucaoMensal:
    def test_ordenado_por_mes(self, pedidos_simples):
        res = analise_evolucao_mensal(pedidos_simples)
        periodos = res.tabela["ano_mes"].tolist()
        assert periodos == sorted(periodos)

    def test_primeiro_variacao_nulo(self, pedidos_simples):
        res = analise_evolucao_mensal(pedidos_simples)
        # Primeiro mês não tem variação
        assert pd.isna(res.tabela.iloc[0]["variacao_pct"])

    def test_hipoteses_eh_lista(self, pedidos_simples):
        res = analise_evolucao_mensal(pedidos_simples)
        assert isinstance(res.hipoteses, list)


# ── Q5 ────────────────────────────────────────────────────────────────────────

class TestCanalAquisicao:
    def test_canais_presentes(self, pedidos_simples, clientes_simples):
        res = analise_canal_aquisicao(pedidos_simples, clientes_simples)
        canais = set(res.tabela["canal_aquisicao"])
        assert "orgânico" in canais

    def test_taxa_entre_0_e_100(self, pedidos_simples, clientes_simples):
        res = analise_canal_aquisicao(pedidos_simples, clientes_simples)
        taxas = res.tabela["taxa_cancelamento_pct"]
        assert (taxas >= 0).all() and (taxas <= 100).all()

    def test_maior_cancelamento_eh_string(self, pedidos_simples, clientes_simples):
        res = analise_canal_aquisicao(pedidos_simples, clientes_simples)
        assert isinstance(res.maior_cancelamento, str)


# ── Limpeza ───────────────────────────────────────────────────────────────────

class TestLimpeza:
    def test_imputa_nulos_valor_total(self):
        df = pd.DataFrame({
            "id": [1, 2, 3],
            "cliente_id": [1, 1, 1],
            "data_pedido": pd.to_datetime(["2023-05-01", "2024-01-01", "2023-08-01"]),
            "status": ["entregue", "entregue", "cancelado"],
            "valor_total": [100.0, None, 200.0],
            "canal_venda": ["site", "site", "app"],
            "cupom_desconto": ["não", "não", "sim"],
        })
        rel = RelatorioLimpeza()
        df_limpo = _clean_pedidos(df, rel)
        assert df_limpo["valor_total"].isna().sum() == 0
        assert len(rel.entradas) >= 1

    def test_preenche_desconto_nulo_com_zero(self):
        df = pd.DataFrame({
            "id": [1, 2],
            "pedido_id": [1, 2],
            "produto_id": [10, 20],
            "quantidade": [1, 2],
            "preco_praticado": [100.0, 200.0],
            "desconto_aplicado": [None, 0.1],
        })
        rel = RelatorioLimpeza()
        df_limpo = _clean_itens_pedido(df, rel)
        assert df_limpo["desconto_aplicado"].iloc[0] == 0.0
        assert rel.entradas[0]["acao"] == "preenchido com 0.0 (sem desconto)"
