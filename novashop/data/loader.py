"""
Camada de acesso a dados: carregamento, validação e limpeza dos CSVs.
Toda interação com o sistema de arquivos passa por este módulo.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

from novashop.config import DATA_FILES

logger = logging.getLogger(__name__)


# ── Estrutura que agrupa todos os DataFrames carregados ──────────────────────

@dataclass
class Dataset:
    pedidos:         pd.DataFrame = field(default_factory=pd.DataFrame)
    clientes:        pd.DataFrame = field(default_factory=pd.DataFrame)
    itens_pedido:    pd.DataFrame = field(default_factory=pd.DataFrame)
    produtos:        pd.DataFrame = field(default_factory=pd.DataFrame)
    avaliacoes:      pd.DataFrame = field(default_factory=pd.DataFrame)
    tickets_suporte: pd.DataFrame = field(default_factory=pd.DataFrame)


# ── Carregamento ─────────────────────────────────────────────────────────────

def _load_csv(path: Path, parse_dates: list[str] | None = None) -> pd.DataFrame:
    """Carrega um CSV com tratamento de erro explícito."""
    if not path.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {path}")
    df = pd.read_csv(path, parse_dates=parse_dates)
    logger.debug("Carregado %s  →  %d linhas, %d colunas", path.name, *df.shape)
    return df


def load_all() -> Dataset:
    """Carrega e retorna todos os arquivos de dados."""
    return Dataset(
        pedidos        = _load_csv(DATA_FILES["pedidos"],        ["data_pedido"]),
        clientes       = _load_csv(DATA_FILES["clientes"],       ["data_cadastro"]),
        itens_pedido   = _load_csv(DATA_FILES["itens_pedido"]),
        produtos       = _load_csv(DATA_FILES["produtos"]),
        avaliacoes     = _load_csv(DATA_FILES["avaliacoes"],     ["data_avaliacao"]),
        tickets_suporte= _load_csv(DATA_FILES["tickets_suporte"],["data_abertura", "data_resolucao"]),
    )


# ── Limpeza e tratamento de inconsistências (Questão 6) ──────────────────────

@dataclass
class RelatorioLimpeza:
    """Registra cada decisão de tratamento de dados para documentação."""
    entradas: list[dict] = field(default_factory=list)

    def registrar(self, tabela: str, campo: str, problema: str,
                  quantidade: int, acao: str) -> None:
        self.entradas.append({
            "tabela":     tabela,
            "campo":      campo,
            "problema":   problema,
            "quantidade": quantidade,
            "acao":       acao,
        })

    def to_dataframe(self) -> pd.DataFrame:
        return pd.DataFrame(self.entradas)


def clean_dataset(ds: Dataset) -> tuple[Dataset, RelatorioLimpeza]:
    """
    Aplica todas as regras de limpeza e retorna o Dataset limpo
    junto de um relatório que documenta cada intervenção.
    """
    relatorio = RelatorioLimpeza()

    ds.pedidos       = _clean_pedidos(ds.pedidos, relatorio)
    ds.itens_pedido  = _clean_itens_pedido(ds.itens_pedido, relatorio)
    ds.avaliacoes    = _clean_avaliacoes(ds.avaliacoes, relatorio)
    ds.tickets_suporte = _clean_tickets(ds.tickets_suporte, relatorio)

    return ds, relatorio


def _clean_pedidos(df: pd.DataFrame, rel: RelatorioLimpeza) -> pd.DataFrame:
    """Trata nulos em valor_total e remove datas inválidas."""
    # valor_total nulo: imputa a mediana — mantém distribuição sem criar outliers
    nulos = df["valor_total"].isna().sum()
    if nulos:
        mediana = df["valor_total"].median()
        df["valor_total"] = df["valor_total"].fillna(mediana)
        rel.registrar("pedidos", "valor_total", "nulo", nulos,
                       f"imputado com mediana (R$ {mediana:,.2f})")

    # Datas fora do intervalo esperado (2023-2024)
    invalidas = (~df["data_pedido"].between("2023-01-01", "2024-12-31")).sum()
    if invalidas:
        df = df[df["data_pedido"].between("2023-01-01", "2024-12-31")]
        rel.registrar("pedidos", "data_pedido", "fora do período 2023-2024",
                       invalidas, "linhas removidas")

    return df


def _clean_itens_pedido(df: pd.DataFrame, rel: RelatorioLimpeza) -> pd.DataFrame:
    """Trata desconto_aplicado nulo e quantidades zero ou negativas."""
    nulos = df["desconto_aplicado"].isna().sum()
    if nulos:
        df["desconto_aplicado"] = df["desconto_aplicado"].fillna(0.0)
        rel.registrar("itens_pedido", "desconto_aplicado", "nulo", nulos,
                       "preenchido com 0.0 (sem desconto)")

    invalidos = (df["quantidade"] <= 0).sum()
    if invalidos:
        df = df[df["quantidade"] > 0]
        rel.registrar("itens_pedido", "quantidade", "valor ≤ 0", invalidos,
                       "linhas removidas")

    return df


def _clean_avaliacoes(df: pd.DataFrame, rel: RelatorioLimpeza) -> pd.DataFrame:
    """Trata comentário nulo e notas fora do intervalo [1, 5]."""
    nulos = df["comentario"].isna().sum()
    if nulos:
        df["comentario"] = df["comentario"].fillna("")
        rel.registrar("avaliacoes", "comentario", "nulo", nulos,
                       "preenchido com string vazia")

    invalidas = (~df["nota"].between(1, 5)).sum()
    if invalidas:
        df = df[df["nota"].between(1, 5)]
        rel.registrar("avaliacoes", "nota", "fora do intervalo [1,5]", invalidas,
                       "linhas removidas")

    return df


def _clean_tickets(df: pd.DataFrame, rel: RelatorioLimpeza) -> pd.DataFrame:
    """Tickets 'aberto' com data_resolucao nula são esperados — documenta mas não altera."""
    abertos_sem_resolucao = (
        df["status"].eq("aberto") & df["data_resolucao"].isna()
    ).sum()
    fechados_sem_resolucao = (
        df["status"].ne("aberto") & df["data_resolucao"].isna()
    ).sum()

    rel.registrar("tickets_suporte", "data_resolucao",
                   "nulo em tickets abertos", abertos_sem_resolucao,
                   "mantido — esperado para tickets em aberto")

    if fechados_sem_resolucao:
        rel.registrar("tickets_suporte", "data_resolucao",
                       "nulo em tickets fechados/resolvidos",
                       fechados_sem_resolucao,
                       "mantido com aviso — requer investigação operacional")

    return df
