
"""
Dashboard Streamlit das faturas PLIN.

Executar:
    .venv\\Scripts\\python.exe -m streamlit run dashboard.py

Dados: lidos do banco SQLite gerado pelo robô (db.py / Teste_Plin_Playwright.py).
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
    padding: 1.25rem 1.1rem;
    border: 1px solid var(--plin-preto);
}}
[data-testid="stMetricLabel"] {{
    font-family: 'Stack Sans Text', 'Segoe UI', Arial, sans-serif;
    font-weight: 600;
    font-size: 0.95rem;
    letter-spacing: 0.5px;
    text-transform: uppercase;
    color: var(--plin-branco);
}}
[data-testid="stMetricValue"] {{
    font-family: 'Stack Sans Notch', 'Segoe UI', Arial, sans-serif;
    font-weight: 700;
    font-size: 1.75rem;
    line-height: 1.15;
    white-space: nowrap;
    color: var(--plin-verde);
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
    ).dt.strftime("%b/%Y")

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

    mostrar_tabela = st.checkbox(
        "Mostrar tabela detalhada",
        value=True,
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
kpi_arvores = com_boleto["saved_trees"].sum()
kpi_consumo = dados["kwh_consumed"].sum()
kpi_compensado = dados["kwh_compensado"].sum()

col1, col2, col3, col4, col5 = st.columns(5)

with col1:
    st.metric(
        "Valor de faturas PLIN",
        formato_real(kpi_fatura_plin),
        help="Soma do valor das faturas da PLIN (bill_cost).",
    )

with col2:
    st.metric(
        "Valor de faturas COPEL",
        formato_real(kpi_fatura_copel),
        help="Soma do valor das faturas da concessionária (dealership_bill_cost).",
    )

with col3:
    st.metric(
        "Iluminação pública",
        formato_real(kpi_iluminacao),
        help="Taxas da concessionária, incl. iluminação pública (dealership_extra_fees).",
    )

with col4:
    st.metric(
        "Valor de desconto",
        formato_real(kpi_desconto),
        help="Economia total gerada pela PLIN (saved_money).",
    )

with col5:
    st.metric(
        "Valor de desconto líquido",
        formato_real(kpi_desconto_liquido),
        help="Desconto total menos a iluminação pública.",
    )

col6, col7, col8, col9 = st.columns(4)

with col6:
    st.metric(
        "CO₂ evitado",
        f"{formato_compacto(kpi_co2)} kg",
        help="Total de CO₂ que deixou de ser emitido.",
    )

with col7:
    st.metric(
        "Árvores poupadas",
        formato_compacto(kpi_arvores),
        help="Equivalência em árvores preservadas.",
    )

with col8:
    st.metric(
        "Consumo total",
        f"{formato_compacto(kpi_consumo)} kWh",
        help="Consumo medido nas faturas.",
    )

with col9:
    st.metric(
        "Energia compensada",
        f"{formato_compacto(abs(kpi_compensado))} kWh",
        help="Energia injetada/compensada na rede.",
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
    ).dt.strftime("%b/%Y")

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
    ).dt.strftime("%b/%Y")

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
# TABELA DETALHADA
# =============================================================================

if mostrar_tabela:

    st.divider()
    st.subheader("Faturas")

    colunas_tabela = {
        "competencia": "Competência",
        "uc": "UC",
        "razao_social": "Razão social",
        "kwh_consumed": "Consumo (kWh)",
        "kwh_compensado": "Compensado (kWh)",
        "consumption_flag": "Bandeira",
        "dealership_bill_cost": "Custo concess. (R$)",
        "bill_cost": "Valor fatura (R$)",
        "saved_money": "Economia (R$)",
        "saved_co2_kg": "CO₂ (kg)",
        "saved_trees": "Árvores",
        "desconto": "Desconto",
        "bill_status": "Status",
        "bill_pdf_url": "PDF",
    }

    colunas_existentes = [
        c for c in colunas_tabela
        if c in dados.columns
    ]

    tabela = dados[colunas_existentes].copy()

    tabela = tabela.rename(
        columns=colunas_tabela
    )

    tabela["Desconto"] = pd.to_numeric(
        tabela["Desconto"],
        errors="coerce"
    )

    def formatar_desconto(valor):
        if pd.isna(valor):
            return "—"
        return f"{valor:.1%}"

    if "Desconto" in tabela.columns:
        tabela["Desconto"] = tabela["Desconto"].apply(
            formatar_desconto
        )

    def formatar_pdf(url):
        if not url:
            return ""
        return f"[PDF]({url})"

    if "PDF" in tabela.columns:
        tabela["PDF"] = tabela["PDF"].apply(
            formatar_pdf
        )

    st.dataframe(
        tabela,
        width="stretch",
        hide_index=True,
    )

    csv_bytes = tabela.to_csv(
        index=False
    ).encode("utf-8")

    st.download_button(
        "Baixar CSV filtrado",
        data=csv_bytes,
        file_name="faturas_plin.csv",
        mime="text/csv",
    )


# =============================================================================
# RODAPÉ
# =============================================================================

st.divider()

st.caption(
    "Dashboard gerado automaticamente a partir dos dados "
    "coletados pelo robô PLIN."
)
