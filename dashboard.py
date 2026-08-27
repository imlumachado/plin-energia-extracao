
"""
Dashboard Streamlit das faturas PLIN.

Rodar:
    .venv\\Scripts\\python.exe -m streamlit run dashboard.py

Os dados vêm do banco SQLite gerado pelo robô (db.py / Teste_Plin_Playwright.py).
"""

import base64
import os
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

import db


# =============================================================================
# CONFIGURAÇÃO DA PÁGINA
# =============================================================================

st.set_page_config(
    page_title="PLIN Energia - Dashboard",
    page_icon=None,
    layout="wide",
    initial_sidebar_state="expanded",
)

COR_PRIMARIA = "#02DE81"
COR_ECONOMIA = "#02DE81"
COR_CUSTO = "#0C0D0E"
COR_CONSUMO = "#2F532E"
COR_BRANCO = "#FFFFFF"
COR_PRETO = "#0C0D0E"
COR_VERDE_ESCURO = "#2F532E"
COR_VERDE_CLARO = "#D4E9D6"

PALETA_PLIN = [
    "#02DE81",
    "#0C0D0E",
    "#2F532E",
    "#D4E9D6",
    "#706F6F",
]

FATOR_EMISSAO_KG_KWH = 0.073

MESES_PT = {
    1: "jan", 2: "fev", 3: "mar", 4: "abr",
    5: "mai", 6: "jun", 7: "jul", 8: "ago",
    9: "set", 10: "out", 11: "nov", 12: "dez",
}


def _mes_pt(dt_obj):
    return f"{MESES_PT[dt_obj.month]}/{dt_obj.year}"


def _fonte_embed(arquivo):
    dados = base64.b64encode(
        arquivo.read_bytes()
    ).decode("ascii")

    formato = (
        "opentype"
        if arquivo.suffix.lower() == ".otf"
        else "truetype"
    )

    mime = (
        "font/otf"
        if arquivo.suffix.lower() == ".otf"
        else "font/ttf"
    )

    return (
        "src: url("
        f"data:{mime};base64,{dados}"
        f") format('{formato}');"
    )


_PESOS_FONTE = {
    "light": 300,
    "medium": 500,
    "semibold": 600,
    "bold": 700,
    "regular": 400,
}


def _fonte_stacksans():
    pasta = Path(__file__).resolve().parent / "fontes"

    if not pasta.is_dir():
        return ""

    faces = []

    for arquivo in sorted(pasta.iterdir()):
        if arquivo.suffix.lower() not in (".otf", ".ttf"):
            continue

        nome = arquivo.stem.lower()

        if "stack" not in nome:
            continue

        familia = (
            "Stack Sans Notch"
            if "notch" in nome
            else "Stack Sans Text"
        )

        peso = 400
        for chave, valor in _PESOS_FONTE.items():
            if chave in nome:
                peso = valor

        faces.append(
            "@font-face {"
            f"font-family: '{familia}';"
            f"font-weight: {peso};"
            "font-style: normal;"
            "font-display: swap;"
            f"{_fonte_embed(arquivo)}"
            "}"
        )

    return "\n".join(faces)


def aplicar_estilo():
    faces = _fonte_stacksans()

    css = f"""
{faces}

:root {{
    --plin-verde: #02DE81;
    --plin-verde-escuro: #2F532E;
    --plin-verde-claro: #D4E9D6;
    --plin-preto: #0C0D0E;
    --plin-branco: #FFFFFF;
    --plin-cinza: #E0E0E0;
}}

html, body, .stApp, [data-testid="stAppViewContainer"],
[data-testid="stSidebar"] {{
    font-family: 'Stack Sans Text', 'Segoe UI', Arial, sans-serif;
}}

[data-testid="stAppViewContainer"] {{
    background-color: var(--plin-branco);
    color: var(--plin-preto);
}}

[data-testid="stHeader"] {{
    background: transparent;
}}

h1, h2, h3, h4, h5 {{
    font-family: 'Stack Sans Notch', 'Segoe UI', Arial, sans-serif;
    font-weight: 700;
    letter-spacing: -0.5px;
    color: var(--plin-preto);
}}
h1 {{ font-size: 2.6rem; }}
h2 {{ font-size: 2rem; }}
h3 {{ font-size: 1.5rem; }}

[data-testid="stMarkdown"] p {{
    color: var(--plin-preto);
    font-size: 1.05rem;
}}

[data-testid="stMetric"] {{
    background-color: var(--plin-preto);
    border-radius: 10px;
    padding: 1rem 1rem;
    border: 1px solid var(--plin-preto);
    height: 100%;
}}
[data-testid="stMetricLabel"] {{
    font-family: 'Stack Sans Text', 'Segoe UI', Arial, sans-serif;
    font-weight: 600;
    font-size: 0.78rem;
    letter-spacing: 0.3px;
    text-transform: uppercase;
    line-height: 1.25;
    display: block;
    color: var(--plin-branco);
}}
[data-testid="stMetricValue"] {{
    font-family: 'Stack Sans Notch', 'Segoe UI', Arial, sans-serif;
    font-weight: 700;
    font-size: 1.45rem;
    line-height: 1.15;
    white-space: normal;
    color: var(--plin-verde);
    margin-top: 0.25rem;
}}

[data-testid="stSidebar"] {{
    background-color: var(--plin-branco);
    border-right: 1px solid var(--plin-cinza);
}}
[data-testid="stSidebar"] p,
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] .stCaption,
[data-testid="stSidebar"] .stMarkdown {{
    color: var(--plin-preto);
}}
[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3 {{
    color: var(--plin-preto);
}}

[data-testid="stTabs"] button p {{
    font-family: 'Stack Sans Text', 'Segoe UI', Arial, sans-serif;
    font-weight: 600;
    font-size: 1.1rem;
    color: var(--plin-preto);
}}
[data-testid="stTabs"] button[aria-selected="true"] p {{
    color: var(--plin-verde);
}}

.stButton button,
[data-testid="stDownloadButton"] button {{
    background-color: var(--plin-preto);
    color: var(--plin-branco);
    font-family: 'Stack Sans Text', 'Segoe UI', Arial, sans-serif;
    font-weight: 600;
    border-radius: 6px;
    border: 2px solid var(--plin-preto);
}}
.stButton button:hover,
[data-testid="stDownloadButton"] button:hover {{
    background-color: var(--plin-verde);
    border-color: var(--plin-verde);
    color: var(--plin-preto);
}}
"""
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)


def estilo_grafico(fig):
    fig.update_layout(
        font=dict(
            family="Stack Sans Text, Segoe UI, Arial",
            size=13,
            color="#0C0D0E",
        ),
        title_font=dict(
            family="Stack Sans Notch, Segoe UI, Arial",
            size=20,
            color="#0C0D0E",
        ),
        paper_bgcolor="#FFFFFF",
        plot_bgcolor="#FFFFFF",
        xaxis=dict(
            tickfont=dict(color="#0C0D0E", size=12),
        ),
        yaxis=dict(
            tickfont=dict(color="#0C0D0E", size=12),
        ),
        legend=dict(
            font=dict(color="#0C0D0E"),
        ),
        hoverlabel=dict(
            bgcolor="#FFFFFF",
            font=dict(color="#0C0D0E"),
        ),
    )

    return fig


aplicar_estilo()


# =============================================================================
# CARREGAMENTO DOS DADOS
# =============================================================================

def carregar_dados():
    caminho_db = os.getenv(
        "PLIN_DB",
        "saida_plin/plin.db"
    )

    faturas = db.consultar_todas(caminho_db)

    if not faturas:
        return pd.DataFrame()

    df = pd.DataFrame(faturas)

    numericas = [
        "kwh_consumed",
        "kwh_compensado",
        "dealership_bill_cost",
        "dealership_extra_fees",
        "dealership_energy_cost",
        "dealership_energy_cost_without_plin",
        "bill_cost",
        "saved_money",
        "saved_co2_kg",
        "saved_trees",
        "desconto",
        "desconto_final",
        "desconto_uc",
        "paid_amount",
        "left_amount",
    ]

    for campo in numericas:
        df[campo] = pd.to_numeric(
            df[campo],
            errors="coerce"
        )

    df["co2_emitido_kg"] = (
        df["kwh_consumed"] * FATOR_EMISSAO_KG_KWH
    )

    df["tem_boleto_plin"] = (
        df["tem_boleto_plin"].astype(
            bool
        )
    )

    df["competencia"] = df["competencia"].astype(
        str
    )

    df["competencia_label"] = pd.to_datetime(
        df["competencia"],
        format="%Y-%m",
        errors="coerce"
    ).apply(_mes_pt)

    df["competencia_sort"] = df["competencia"]

    df["razao_social"] = df["razao_social"].fillna(
        "Sem identificação"
    )

    df["uc"] = df["uc"].astype(str)

    return df


# =============================================================================
# HELPERS
# =============================================================================

def formato_real(valor):
    if valor is None:
        return "R$ 0,00"

    return f"R$ {valor:,.2f}".replace(
        ",", "X"
    ).replace(
        ".", ","
    ).replace(
        "X", "."
    )


def formato_compacto(valor):
    if valor is None:
        return "0"

    if abs(valor) >= 1_000_000:
        return f"{valor / 1_000_000:.1f} mi"

    if abs(valor) >= 1_000:
        return f"{valor / 1_000:.1f} mil"

    return f"{valor:,.0f}".replace(
        ",", "."
    )


# =============================================================================
# SIDEBAR - FILTROS
# =============================================================================

st.sidebar.title("PLIN Energia")
st.sidebar.caption("Filtros do dashboard")

df = carregar_dados()

if df.empty:
    st.error(
        "Nenhuma fatura encontrada no banco de dados.\n\n"
        "Execute o robô primeiro:\n"
        "```\n"
        ".venv\\Scripts\\python.exe Teste_Plin_Playwright.py\n"
        "```\n"
        "ou carregue dados com:\n"
        "```\n"
        ".venv\\Scripts\\python.exe db.py saida_plin/plin.db faturas_unificadas.json\n"
        "```"
    )
    st.stop()

competencias = sorted(
    df["competencia"].dropna().unique()
)

ucs_ordenadas = sorted(
    df["uc"].unique()
)

with st.sidebar:

    ucs_selecionadas = st.multiselect(
        "Unidades Consumidoras",
        options=ucs_ordenadas,
        default=ucs_ordenadas,
        help="Selecione as UCs a incluir na análise.",
    )

    st.markdown("#### Período")

    intervalo = st.select_slider(
        "Competências",
        options=competencias,
        value=(
            competencias[0],
            competencias[-1],
        ),
    )

    incluir_sem_boleto = st.checkbox(
        "Incluir faturas sem boleto PLIN",
        value=True,
        help=(
            "Faturas recentes que ainda não possuem "
            "economia calculada."
        ),
    )

    st.divider()

    st.caption(
        f"Dados de "
        f"**{competencias[0]}** a "
        f"**{competencias[-1]}**"
    )


# =============================================================================
# APLICAÇÃO DOS FILTROS
# =============================================================================

inicio, fim = intervalo

filtro = (
    (df["uc"].isin(ucs_selecionadas))
    & (df["competencia"] >= inicio)
    & (df["competencia"] <= fim)
)

if not incluir_sem_boleto:
    filtro &= df["tem_boleto_plin"]

dados = df.loc[filtro].copy()

if dados.empty:
    st.warning(
        "Nenhuma fatura corresponde aos filtros selecionados."
    )
    st.stop()


# =============================================================================
# CABEÇALHO
# =============================================================================

st.title("PLIN Energia")

texto_cabecalho = (
    f"Exibindo **{len(dados):,}** faturas de "
    f"**{dados['uc'].nunique():,}** UCs "
    f"({inicio} a {fim})."
)

st.caption(texto_cabecalho)

# =============================================================================
# KPIs
# =============================================================================

com_boleto = dados[dados["tem_boleto_plin"]]

kpi_fatura_plin = com_boleto["bill_cost"].sum()
kpi_fatura_copel = com_boleto["dealership_bill_cost"].sum()
kpi_iluminacao = com_boleto["dealership_extra_fees"].sum()
kpi_desconto = com_boleto["saved_money"].sum()
kpi_desconto_liquido = kpi_desconto - kpi_iluminacao

kpi_co2 = com_boleto["saved_co2_kg"].sum()
kpi_co2_emitido = dados["co2_emitido_kg"].sum()
kpi_arvores = com_boleto["saved_trees"].sum()
kpi_consumo = dados["kwh_consumed"].sum()
kpi_compensado = dados["kwh_compensado"].sum()

kpis = [
    (
        "Valor de faturas PLIN",
        formato_real(kpi_fatura_plin),
        "Soma do valor das faturas da PLIN (bill_cost).",
    ),
    (
        "Valor de faturas COPEL",
        formato_real(kpi_fatura_copel),
        "Soma do valor das faturas da concessionária (dealership_bill_cost).",
    ),
    (
        "Iluminação pública",
        formato_real(kpi_iluminacao),
        "Taxas da concessionária, incl. iluminação pública (dealership_extra_fees).",
    ),
    (
        "Valor de desconto",
        formato_real(kpi_desconto),
        "Economia total gerada pela PLIN (saved_money).",
    ),
    (
        "Valor de desconto líquido",
        formato_real(kpi_desconto_liquido),
        "Desconto total menos a iluminação pública.",
    ),
    (
        "CO₂ evitado",
        f"{formato_compacto(kpi_co2)} kg",
        "Total de CO₂ que deixou de ser emitido.",
    ),
    (
        "CO₂ emitido (est.)",
        f"{formato_compacto(kpi_co2_emitido)} kg",
        (
            "Estimativa das emissões a partir do consumo "
            f"({FATOR_EMISSAO_KG_KWH} kg de CO₂ por kWh, "
            "fator de emissão do SIN/MCTI)."
        ),
    ),
    (
        "Árvores poupadas",
        formato_compacto(kpi_arvores),
        "Equivalência em árvores preservadas.",
    ),
    (
        "Consumo total",
        f"{formato_compacto(kpi_consumo)} kWh",
        "Consumo medido nas faturas.",
    ),
    (
        "Energia compensada",
        f"{formato_compacto(abs(kpi_compensado))} kWh",
        "Energia injetada/compensada na rede.",
    ),
]

KPI_POR_LINHA = 4

for i in range(0, len(kpis), KPI_POR_LINHA):
    bloco = kpis[i:i + KPI_POR_LINHA]

    colunas_kpi = st.columns(len(bloco))

    for coluna, (rotulo, valor, ajuda) in zip(
        colunas_kpi,
        bloco,
    ):
        with coluna:
            st.metric(
                rotulo,
                valor,
                help=ajuda,
            )

st.divider()

# =============================================================================
# GRÁFICO COMPARATIVO - CO2 EMITIDO X EVITADO
# =============================================================================

st.subheader("CO₂ emitido × CO₂ evitado")

serie_co2 = (
    dados
    .groupby("competencia")["co2_emitido_kg"]
    .sum()
    .rename("co2_emitido_kg")
    .to_frame()
    .join(
        com_boleto
        .groupby("competencia")["saved_co2_kg"]
        .sum()
    )
    .fillna(0)
    .reset_index()
)

serie_co2["competencia_label"] = pd.to_datetime(
    serie_co2["competencia"],
    format="%Y-%m",
).apply(_mes_pt)

fig_co2 = go.Figure()

fig_co2.add_trace(
    go.Bar(
        x=serie_co2["competencia_label"],
        y=serie_co2["co2_emitido_kg"],
        name="CO₂ emitido",
        marker_color=COR_CONSUMO,
    )
)

fig_co2.add_trace(
    go.Bar(
        x=serie_co2["competencia_label"],
        y=serie_co2["saved_co2_kg"],
        name="CO₂ evitado",
        marker_color=COR_ECONOMIA,
    )
)

fig_co2.update_layout(
    title="",
    xaxis_title="Competência",
    yaxis_title="kg de CO₂",
    barmode="group",
    height=420,
    margin=dict(l=40, r=20, t=40, b=40),
)

estilo_grafico(fig_co2)

st.plotly_chart(
    fig_co2,
    width="stretch",
)

st.divider()

# =============================================================================
# GRÁFICOS
# =============================================================================

tab_economia, tab_consumo, tab_ucs, tab_bandeira = st.tabs(
    [
        "Economia",
        "Consumo",
        "Por UC",
        "Bandeiras",
    ]
)

# -----------------------------------------------------------------------------
# TAB 1 - ECONOMIA
# -----------------------------------------------------------------------------

with tab_economia:

    serie_economia = (
        com_boleto
        .groupby("competencia")["saved_money"]
        .sum()
        .reindex(sorted(com_boleto["competencia"].unique()))
        .reset_index()
    )

    serie_economia["competencia_label"] = pd.to_datetime(
        serie_economia["competencia"],
        format="%Y-%m",
    ).apply(_mes_pt)

    fig = go.Figure()

    fig.add_trace(
        go.Bar(
            x=serie_economia["competencia_label"],
            y=serie_economia["saved_money"],
            name="Economia",
            marker_color=COR_ECONOMIA,
        )
    )

    fig.update_layout(
        title="Economia gerada por competência",
        xaxis_title="Competência",
        yaxis_title="Economia (R$)",
        height=420,
        margin=dict(l=40, r=20, t=50, b=40),
    )

    estilo_grafico(fig)

    st.plotly_chart(
        fig,
        width="stretch",
    )

# -----------------------------------------------------------------------------
# TAB 2 - CONSUMO
# -----------------------------------------------------------------------------

with tab_consumo:

    serie_consumo = (
        dados
        .groupby("competencia")[["kwh_consumed", "kwh_compensado"]]
        .sum()
        .reset_index()
    )

    serie_consumo["competencia_label"] = pd.to_datetime(
        serie_consumo["competencia"],
        format="%Y-%m",
    ).apply(_mes_pt)

    fig = go.Figure()

    fig.add_trace(
        go.Bar(
            x=serie_consumo["competencia_label"],
            y=serie_consumo["kwh_consumed"],
            name="Consumido",
            marker_color=COR_CONSUMO,
        )
    )

    fig.add_trace(
        go.Bar(
            x=serie_consumo["competencia_label"],
            y=serie_consumo["kwh_compensado"],
            name="Compensado",
            marker_color=COR_ECONOMIA,
        )
    )

    fig.update_layout(
        title="Consumo e energia compensada por competência",
        xaxis_title="Competência",
        yaxis_title="kWh",
        barmode="group",
        height=420,
        margin=dict(l=40, r=20, t=50, b=40),
    )

    estilo_grafico(fig)

    st.plotly_chart(
        fig,
        width="stretch",
    )

# -----------------------------------------------------------------------------
# TAB 3 - POR UC
# -----------------------------------------------------------------------------

with tab_ucs:

    economia_por_uc = (
        com_boleto
        .groupby(["uc", "razao_social"])["saved_money"]
        .sum()
        .sort_values(ascending=False)
        .reset_index()
    )

    economia_por_uc["rotulo"] = (
        economia_por_uc["uc"]
        + " — "
        + economia_por_uc["razao_social"]
    )

    top = economia_por_uc.head(10)

    fig = go.Figure()

    fig.add_trace(
        go.Bar(
            x=top["saved_money"],
            y=top["rotulo"],
            orientation="h",
            marker_color=COR_ECONOMIA,
        )
    )

    fig.update_layout(
        title="Top 10 UCs por economia acumulada",
        xaxis_title="Economia (R$)",
        yaxis_title=None,
        height=500,
        margin=dict(l=20, r=20, t=50, b=40),
    )

    fig.update_yaxes(
        automargin=True,
        tickfont=dict(size=10),
    )

    estilo_grafico(fig)

    st.plotly_chart(
        fig,
        width="stretch",
    )

    consumo_por_uc = (
        dados
        .groupby(["uc", "razao_social"])["kwh_consumed"]
        .sum()
        .sort_values(ascending=False)
        .reset_index()
    )

    consumo_por_uc["rotulo"] = (
        consumo_por_uc["uc"]
        + " — "
        + consumo_por_uc["razao_social"]
    )

    top_consumo = consumo_por_uc.head(10)

    fig2 = go.Figure()

    fig2.add_trace(
        go.Bar(
            x=top_consumo["kwh_consumed"],
            y=top_consumo["rotulo"],
            orientation="h",
            marker_color=COR_CONSUMO,
        )
    )

    fig2.update_layout(
        title="Top 10 UCs por consumo",
        xaxis_title="Consumo (kWh)",
        yaxis_title=None,
        height=500,
        margin=dict(l=20, r=20, t=50, b=40),
    )

    fig2.update_yaxes(
        automargin=True,
        tickfont=dict(size=10),
    )

    estilo_grafico(fig2)

    st.plotly_chart(
        fig2,
        width="stretch",
    )

# -----------------------------------------------------------------------------
# TAB 4 - BANDEIRAS
# -----------------------------------------------------------------------------

with tab_bandeira:

    bandeiras = (
        com_boleto["consumption_flag"]
        .value_counts()
        .reset_index()
    )

    bandeiras.columns = [
        "bandeira",
        "quantidade",
    ]

    fig = go.Figure()

    fig.add_trace(
        go.Pie(
            labels=bandeiras["bandeira"],
            values=bandeiras["quantidade"],
            hole=0.4,
            marker=dict(
                colors=PALETA_PLIN,
                line=dict(
                    color="#FFFFFF",
                    width=2,
                ),
            ),
        )
    )

    fig.update_layout(
        title="Distribuição por bandeira tarifária",
        height=420,
        margin=dict(l=20, r=20, t=50, b=40),
    )

    estilo_grafico(fig)

    st.plotly_chart(
        fig,
        width="stretch",
    )

# =============================================================================
# RODAPÉ
# =============================================================================

st.divider()

st.caption(
    "Dashboard gerado automaticamente a partir dos dados "
    "coletados pelo robô PLIN."
)
