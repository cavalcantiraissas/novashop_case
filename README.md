# NovaShop Analytics

**Case técnico - Peers Group Digital Consulting**  
**Candidata:** Raissa Cavalcanti

---

## Índice

1. [O Problema](#o-problema)
2. [Tecnologias Utilizadas](#tecnologias-utilizadas)
3. [Arquitetura e Decisões de Projeto](#arquitetura-e-decisões-de-projeto)
4. [Estrutura de Arquivos](#estrutura-de-arquivos)
5. [Como Executar](#como-executar)
6. [Questões Respondidas](#questões-respondidas-e-resultados)
7. [Outputs Gerados](#outputs-gerados)
8. [Histórico de Commits](#histórico-de-commits)

---

## O Problema

A **NovaShop** é um e-commerce brasileiro em expansão com operações B2C e B2B, mais de 15.000 pedidos registrados em dois anos e uma base ativa de 3.000 clientes distribuídos por todo o Brasil. A empresa identificou três sintomas preocupantes:

- **Alta taxa de cancelamentos e devoluções** em alguns segmentos
- **Crescimento de tickets de suporte** sem identificação da causa raiz
- **Falta de visibilidade analítica** sobre o comportamento dos dados operacionais

O desafio proposto foi atuar como consultora de Digital Consulting, analisar as bases de dados fornecidas e identificar padrões, anomalias e evidências que expliquem esses problemas - respondendo a seis questões analíticas específicas por meio de código.

---

## Tecnologias Utilizadas

| Tecnologia | Versão mínima | Finalidade |
|---|---|---|
| Python | 3.10+ | Linguagem principal |
| pandas | 2.0 | Manipulação e análise de dados |
| NumPy | 1.24 | Operações numéricas auxiliares |
| SciPy | 1.10 | Teste t de Welch (Q3) |
| Matplotlib | 3.7 | Geração de gráficos |
| pytest | 7.0 | Testes unitários automatizados |

Todas as dependências estão listadas em `requirements.txt`. O projeto roda completamente offline a partir dos CSVs fornecidos.

---

## Arquitetura e Decisões de Projeto

O projeto segue uma **arquitetura em três camadas**, inspirada no padrão MVC adaptado para pipelines de dados:

```
┌─────────────────────────────────────────────────────┐
│                   run.py  (entry point)             │
└──────────────────────┬──────────────────────────────┘
                       │
          ┌────────────▼─────────────┐
          │      novashop/main.py    │  ← Orquestrador
          └──┬──────────┬────────────┘
             │          │
    ┌─────────▼───┐  ┌──▼──────────────┐
    │  data/      │  │  analysis/      │
    │  loader.py  │  │  queries.py     │
    └─────────────┘  └──┬──────────────┘
    Carga + Limpeza      │
                   ┌─────▼──────────────┐
                   │  presentation/     │
                   │  reporter.py       │
                   └────────────────────┘
                   Tabelas + Gráficos
```

**Decisões técnicas relevantes:**

- **Dataclasses tipadas por análise** (`ResultadoStatus`, `ResultadoTicketMedio` etc.) em vez de dicts genéricos - contratos explícitos, autocompletar em IDEs, fácil de mockar em testes.
- **Teste t de Welch** em vez do teste t de Student para a Q3: a proporção B2C/B2B é 80/20, variâncias desiguais são esperadas - Welch não assume homogeneidade de variância.
- **Imputação por mediana** para `valor_total` nulo: distribuição assimétrica (P25=R$795, P75=R$2.288, máx=R$14.999), mediana é mais robusta a outliers que a média.
- **Exclusão de cancelados no ranking de produtos (Q2)**: receita de pedidos cancelados não representa venda efetiva.
- **`RelatorioLimpeza` auditável**: cada intervenção nos dados é registrada com tabela, campo, problema, quantidade e ação - gerando ao final um CSV rastreável.
- **Funções puras na análise**: sem efeitos colaterais, sem estado global — qualquer função pode ser testada isoladamente com fixtures mínimas.

---

## Estrutura de Arquivos

```
novashop_case/
│
├── run.py                          # Ponto de entrada — execute este arquivo
├── requirements.txt                # Dependências do projeto
│
└── novashop/                       # Pacote Python principal
    ├── __init__.py
    ├── config.py                   # Configurações centralizadas
    ├── main.py                     # Orquestrador do pipeline
    │
    ├── data/
    │   └── loader.py               # Carga, validação e limpeza dos CSVs
    │
    ├── analysis/
    │   └── queries.py              # As 6 análises de negócio
    │
    ├── presentation/
    │   └── reporter.py             # Formatação de saídas e geração de gráficos
    │
    ├── tests/
    │   └── test_analysis.py        # 17 testes unitários (pytest)
    │
    └── outputs/                    # Gerado automaticamente na primeira execução
        ├── q1_status_pedidos.png
        ├── q2_top_produtos.png
        ├── q3_ticket_medio.png
        ├── q4_evolucao_mensal.png
        ├── q5_canal_aquisicao.png
        └── q6_relatorio_limpeza.csv
```

### Descrição detalhada de cada arquivo

**`run.py`**  
Ponto de entrada da aplicação. Importa e chama `novashop.main.run()`. Resolve o problema de importação de pacotes sem exigir manipulação manual de `PYTHONPATH` - basta estar na pasta raiz e rodar `python3 run.py`.

**`novashop/config.py`**  
Centraliza todas as configurações: caminhos de dados (com busca automática em múltiplos candidatos), paleta de cores, parâmetros de análise (`TOP_N_PRODUTOS`, `ALPHA_TESTE_T`) e estilo de gráficos. Elimina magic numbers espalhados pelo código.

**`novashop/main.py`**  
Orquestra o pipeline completo em cinco etapas: carga → limpeza → análise → apresentação → sumário. Trata erros críticos explicitamente e mede tempo total de execução.

**`novashop/data/loader.py`**  
Todo contato com o sistema de arquivos passa por aqui. Contém `load_all()`, `clean_dataset()`, funções privadas `_clean_*` por tabela e a classe `RelatorioLimpeza`.

**`novashop/analysis/queries.py`**  
As seis análises de negócio como funções puras. Cada uma retorna uma dataclass tipada. O dicionário `_CONTEXTO_MENSAL` cobre todos os 12 meses do calendário comercial brasileiro para geração automática de hipóteses de sazonalidade.

**`novashop/presentation/reporter.py`**  
Responsável exclusivamente por exibição. Funções `exibir_*` formatam tabelas no terminal; funções `_plotar_*` geram e salvam gráficos Matplotlib. A separação garante que análises sejam testáveis sem depender de saída visual.

**`novashop/tests/test_analysis.py`**  
17 testes unitários em 6 classes. Fixtures mínimas e independentes dos CSVs reais. Cobre contagem, percentual, exclusão de cancelados, p-valor, ordenação temporal, limpeza de nulos e edge cases do teste t.

---

## Como Executar

```bash
# 1. Crie um ambiente virtual
python3 -m venv venv
source venv/bin/activate

# 2. Instale as dependências
pip install -r novashop/requirements.txt

# 3. Execute o projeto
python run.py
```
---

## Questões Respondidas 

### Q1 - Volume de Pedidos por Status

### Q2 - Top 10 Produtos Mais Vendidos

### Q3 - Ticket Médio por Segmento

### Q4 - Evolução Mensal (2023–2024)

### Q5 - Canal de Aquisição

### Q6 - Inconsistências

---

## Outputs Gerados

| Arquivo | Descrição |
|---|---|
| `q1_status_pedidos.png` | Barras + pizza com distribuição por status |
| `q2_top_produtos.png` | Barras horizontais duplas: quantidade e receita |
| `q3_ticket_medio.png` | Barras comparativas B2C vs B2B com p-valor |
| `q4_evolucao_mensal.png` | Linha temporal com destaque de pico e mínimo |
| `q5_canal_aquisicao.png` | Barras duplas: cancelamento e ticket por canal |
| `q6_relatorio_limpeza.csv` | Tabela auditável de todas as intervenções nos dados |
