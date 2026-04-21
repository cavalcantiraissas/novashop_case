"""
Configurações centralizadas do projeto NovaShop.
Mantém caminhos, constantes e parâmetros de análise em um único lugar.
"""

from pathlib import Path

# ── Diretórios ──────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).parent

# Procura os CSVs primeiro ao lado do pacote novashop/, depois no diretório
# de uploads do ambiente de desenvolvimento original.
_candidatos_data = [
    Path("/mnt/user-data/uploads"), # servidor de desenvolvimento
    BASE_DIR.parent / "data",       # ../data/  (uso local — recomendado)
    BASE_DIR.parent,                # ../  (CSVs soltos junto do run.py)
]
DATA_DIR = next((p for p in _candidatos_data if p.exists()), BASE_DIR.parent)

OUTPUT_DIR = BASE_DIR / "outputs"
OUTPUT_DIR.mkdir(exist_ok=True)

# ── Arquivos de dados ────────────────────────────────────────────────────────
DATA_FILES = {
    "pedidos":        DATA_DIR / "pedidos.csv",
    "clientes":       DATA_DIR / "clientes.csv",
    "itens_pedido":   DATA_DIR / "itens_pedido.csv",
    "produtos":       DATA_DIR / "produtos.csv",
    "avaliacoes":     DATA_DIR / "avaliacoes.csv",
    "tickets_suporte": DATA_DIR / "tickets_suporte.csv",
}

# ── Parâmetros de análise ────────────────────────────────────────────────────
TOP_N_PRODUTOS = 10
ALPHA_TESTE_T  = 0.05       # nível de significância para o teste t
ANOS_ANALISE   = [2023, 2024]

# ── Paleta de cores para gráficos ───────────────────────────────────────────
CORES = {
    "primaria":   "#1C7293",
    "secundaria": "#065A82",
    "acento":     "#21295C",
    "alerta":     "#E87040",
    "sucesso":    "#2E8B57",
    "neutro":     "#AAAAAA",
    "b2c":        "#1C7293",
    "b2b":        "#E87040",
    "status": {
        "entregue":    "#2E8B57",
        "em_transito": "#1C7293",
        "cancelado":   "#C0392B",
        "devolvido":   "#E87040",
    },
}

ESTILO_GRAFICO = {
    "figura_tamanho": (10, 6),
    "dpi": 150,
    "fonte_titulo": 14,
    "fonte_eixo":   11,
}
