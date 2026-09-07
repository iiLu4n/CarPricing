from pathlib import Path
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

# -----------------------------------------------------------------------------
# Configuração da página (Premium Modern UI)
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="CarPricing",
    page_icon="🚘",
    layout="wide",
)

st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@300;400;600;700&display=swap');
        
        .stApp { 
            background-color: #0b0f19; 
            color: #e2e8f0; 
            font-family: 'Montserrat', sans-serif; 
        }
        .sidebar .stSidebar { 
            background-color: #111827; 
            border-right: 1px solid #1f2937; 
        }
        h1, h2, h3, h4, h5 { 
            font-family: 'Montserrat', sans-serif !important; 
            color: #ffffff !important; 
            font-weight: 600 !important;
            letter-spacing: -0.5px;
        }
        p, span, label, div { 
            font-family: 'Montserrat', sans-serif !important; 
        }
        .header-box {
            background: linear-gradient(135deg, #1e3a8a 0%, #3b82f6 100%);
            padding: 24px;
            border-radius: 12px;
            color: white;
            margin-bottom: 30px;
            box-shadow: 0 10px 25px rgba(59, 130, 246, 0.2);
            text-align: center;
        }
        .header-box h1 {
            margin: 0;
            font-size: 2.2rem;
            font-weight: 700;
        }
        .header-box p {
            margin: 5px 0 0 0;
            opacity: 0.9;
            font-size: 1.1rem;
        }
    </style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# Extração e Transformação de Dados (ETL)
# -----------------------------------------------------------------------------
@st.cache_data
def get_premium_pricing_data():
    caminho_base = Path(__file__).parent / "data/bmw_inteligencia_mercado_completo.csv"
    caminho_fallback = Path("bmw_inteligencia_mercado_completo.csv")
    
    arquivo_olx = caminho_base if caminho_base.exists() else caminho_fallback
    if not arquivo_olx.exists():
        st.error("❌ ERRO: Base de dados estruturada não localizada.")
        return pd.DataFrame()

    df = pd.read_csv(arquivo_olx)
    df = df[df["Preco"] > 0].copy()

    df["KM_Int"] = pd.to_numeric(
        df["KM"].astype(str).str.replace(r"\D", "", regex=True), errors="coerce"
    ).fillna(0)
    df["Ano"] = pd.to_numeric(df["Ano"], errors="coerce").fillna(0)
    df['Municipio'] = df['Municipio'].astype(str).str.strip()
    df['Opcionais'] = df['Opcionais'].fillna("N/A").astype(str)
    
    # Garantir que a coluna de Versão esteja bem tratada para o novo gráfico
    if 'Versao' in df.columns:
        df['Versao'] = df['Versao'].fillna("Não Informada").astype(str)
    else:
        df['Versao'] = "Única"

    caminho_geo = Path(__file__).parent / "data/municipios_coordenadas.csv"
    caminho_geo_fallback = Path("municipios_coordenadas_base.csv")
    
    arquivo_geo = caminho_geo if caminho_geo.exists() else caminho_geo_fallback
    if arquivo_geo.exists():
        df_geo = pd.read_csv(arquivo_geo)
        df_geo['Municipio'] = df_geo['Municipio'].astype(str).str.strip()
        df = pd.merge(df, df_geo, on="Municipio", how="left")
        df["lat"] = df["lat"].fillna(-23.5505)
        df["lon"] = df["lon"].fillna(-46.6333)
    else:
        df["lat"] = -23.5505
        df["lon"] = -46.6333

    return df

df = get_premium_pricing_data()
if df.empty:
    st.stop()

# Higienização de Opcionais para o Filtro Dinâmico
opcionais_brutos = df['Opcionais'].str.split(',').explode().str.strip().str.title()
opcionais_validos = opcionais_brutos[~opcionais_brutos.isin(['N/A', 'N/a', 'None', '', 'Nan'])].dropna().unique()
opcionais_disponiveis = sorted(opcionais_validos)

# -----------------------------------------------------------------------------
# Interface e Filtros Dinâmicos
# -----------------------------------------------------------------------------
st.markdown("""
    <div class="header-box">
        <h1>CarPricing Analytics</h1>
        <p>Inteligência de Mercado e Precificação de Ativos Premium</p>
    </div>
""", unsafe_allow_html=True)

st.sidebar.markdown("### 🎛️ Filtros de Mercado")

modelos_disponiveis = sorted(df["Modelo"].dropna().unique().tolist())
modelo_selecionado = st.sidebar.multiselect("Modelos", modelos_disponiveis, default=modelos_disponiveis)

combustiveis_disponiveis = sorted(df["Combustivel"].dropna().unique().tolist())
combustivel_selecionado = st.sidebar.multiselect("Motorização", combustiveis_disponiveis, default=combustiveis_disponiveis)

municipios_disponiveis = sorted(df["Municipio"].dropna().unique().tolist())
municipio_selecionado = st.sidebar.multiselect("Praças (Municípios)", municipios_disponiveis, default=municipios_disponiveis)

min_ano, max_ano = int(df["Ano"].min()), int(df["Ano"].max())
anos_filtro = st.sidebar.slider("Período de Fabricação", min_value=min_ano, max_value=max_ano, value=[min_ano, max_ano])

opcionais_selecionados = st.sidebar.multiselect("Filtrar por Opcionais", opcionais_disponiveis, default=[])

df_filtrado = df[
    (df["Modelo"].isin(modelo_selecionado)) & 
    (df["Combustivel"].isin(combustivel_selecionado)) & 
    (df["Municipio"].isin(municipio_selecionado)) & 
    (df["Ano"] >= anos_filtro[0]) & 
    (df["Ano"] <= anos_filtro[1])
]

# Lógica de Filtro Restritivo (AND) para Opcionais
if opcionais_selecionados:
    for opcional in opcionais_selecionados:
        df_filtrado = df_filtrado[df_filtrado['Opcionais'].str.contains(opcional, case=False, na=False, regex=False)]

# -----------------------------------------------------------------------------
# KPIs Macro (Métricas Principais)
# -----------------------------------------------------------------------------
total_ativos = len(df_filtrado)
ticket_medio = df_filtrado["Preco"].mean() if total_ativos > 0 else 0
km_medio = df_filtrado["KM_Int"].mean() if total_ativos > 0 else 0

col1, col2, col3 = st.columns(3)
col1.metric("Volume de Ativos", f"{total_ativos} un")
col2.metric("Ticket Médio", f"R$ {ticket_medio:,.0f}".replace(",", "."))
col3.metric("Desgaste Médio", f"{km_medio:,.0f} km".replace(",", "."))
st.markdown("<br>", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 1. Gráfico Interativo: Volume por Modelo e Ano (Com Filtro Rerun)
# -----------------------------------------------------------------------------
st.markdown("#### 💎 Dinâmica de Volume por Modelo e Ano (Clique na linha para filtrar)")

if not df_filtrado.empty:
    df_vol_modelo = df_filtrado.groupby(["Ano", "Modelo"]).size().reset_index(name="Volume")
    df_vol_modelo = df_vol_modelo.sort_values("Ano")

    fig_vol_model = px.line(
        df_vol_modelo, x="Ano", y="Volume", color="Modelo", 
        markers=True, template="plotly_dark",
        custom_data=["Modelo"], # Permite capturar o nome do modelo ao clicar
        color_discrete_sequence=px.colors.qualitative.Pastel
    )
    fig_vol_model.update_traces(line_shape='spline', line=dict(width=3), marker=dict(size=8, opacity=0.9))
    fig_vol_model.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", 
        hovermode="x unified", transition_duration=500, margin=dict(t=10, b=10)
    )
    
    evento_clique = st.plotly_chart(fig_vol_model, use_container_width=True, on_select="rerun", selection_mode="points")
    
    if len(evento_clique.selection.points) > 0:
        modelo_selecionado_grafico = evento_clique.selection.points[0]["customdata"][0]
        df_filtrado = df_filtrado[df_filtrado["Modelo"] == modelo_selecionado_grafico]
        st.success(f"Filtro Automático Ativo: {modelo_selecionado_grafico} (Limpe a seleção no gráfico para restaurar)")
else:
    st.info("Sem dados suficientes para modelagem.")

st.markdown("<br>", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 2. Novo Gráfico Bem Estruturado: Treemap (Modelo > Versão > Ano)
# -----------------------------------------------------------------------------
st.markdown("#### 📑 Estrutura de Estoque: Categorização por Modelo, Versão e Ano")
st.markdown("<p style='opacity: 0.8; font-size: 0.9rem; margin-top: -10px;'>A hierarquia dos blocos reflete a concentração de volume (quanto maior o bloco, maior o estoque na praça).</p>", unsafe_allow_html=True)

if not df_filtrado.empty:
    df_hierarquia = df_filtrado.groupby(["Modelo", "Versao", "Ano"]).size().reset_index(name="Volume")
    
    fig_tree = px.treemap(
        df_hierarquia, 
        path=["Modelo", "Versao", "Ano"], 
        values="Volume",
        color="Volume",
        color_continuous_scale="Tealgrn",
        template="plotly_dark"
    )
    
    fig_tree.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", 
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(t=10, l=10, r=10, b=10)
    )
    
    fig_tree.update_traces(
        textinfo="label+value", 
        hovertemplate="<b>%{label}</b><br>Volume: %{value}<extra></extra>"
    )
    
    st.plotly_chart(fig_tree, use_container_width=True)

st.markdown("<br>", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# Inteligência Geográfica (Mapa centralizado em SP por padrão)
# -----------------------------------------------------------------------------
st.markdown("#### 🗺️ Dispersão Geográfica e Fluxo de Capital")
if not df_filtrado.empty:
    df_mapa = df_filtrado.groupby(["Municipio", "lat", "lon"]).agg(Volume=("Preco", "count"), Ticket_Medio=("Preco", "mean")).reset_index()
    fig_geo = px.scatter_map(
        df_mapa, lat="lat", lon="lon", size="Volume", color="Ticket_Medio",
        hover_name="Municipio", hover_data={"Volume": True, "Ticket_Medio": ":.2f", "lat": False, "lon": False},
        color_continuous_scale="Tealgrn", zoom=6, height=450, map_style="carto-darkmatter",
        center={"lat": -23.5505, "lon": -46.6333} # Garante a localização travada em São Paulo
    )
    fig_geo.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", margin=dict(l=0, r=0, t=10, b=0))
    st.plotly_chart(fig_geo, use_container_width=True)

st.markdown("<br>", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# Visualizações Avançadas e Evolutivas
# -----------------------------------------------------------------------------
col_g1, col_g2 = st.columns(2)

with col_g1:
    st.markdown("#### 🔋 Distribuição de Preço por Motorização")
    if not df_filtrado.empty:
        fig_box = px.box(
            df_filtrado, x="Combustivel", y="Preco", color="Combustivel",
            template="plotly_dark", points="all",
            color_discrete_sequence=px.colors.qualitative.Safe
        )
        fig_box.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            showlegend=False, transition_duration=500, margin=dict(t=10)
        )
        st.plotly_chart(fig_box, use_container_width=True)

with col_g2:
    st.markdown("#### 📈 Evolução de Ticket Médio por Ano e Combustível")
    if not df_filtrado.empty:
        df_ano_comb = df_filtrado.groupby(['Ano', 'Combustivel'])['Preco'].mean().reset_index().sort_values('Ano')
        
        fig_linha_preco = px.line(
            df_ano_comb, x="Ano", y="Preco", color="Combustivel",
            markers=True, template="plotly_dark",
            color_discrete_sequence=px.colors.qualitative.Safe
        )
        fig_linha_preco.update_traces(line_shape='spline', line=dict(width=3), marker=dict(size=8, opacity=0.9))
        fig_linha_preco.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", 
            hovermode="x unified", transition_duration=500, margin=dict(t=10)
        )
        st.plotly_chart(fig_linha_preco, use_container_width=True)

st.markdown("<br>", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# Gráfico Dual: Volume de Modelos x Média de KM por Ano
# -----------------------------------------------------------------------------
st.markdown("#### 🛣️ Relação Volume de Ativos x Desgaste (KM) por Ano")
if not df_filtrado.empty:
    df_ano_metricas = df_filtrado.groupby('Ano').agg(
        Volume=('Modelo', 'count'),
        KM_Medio=('KM_Int', 'mean')
    ).reset_index().sort_values('Ano')
    
    fig_dual = make_subplots(specs=[[{"secondary_y": True}]])
    
    fig_dual.add_trace(
        go.Scatter(
            x=df_ano_metricas['Ano'], y=df_ano_metricas['Volume'],
            name="Volume de Ativos", mode='lines+markers',
            line=dict(shape='spline', width=3, color='#3b82f6'),
            marker=dict(size=8)
        ),
        secondary_y=False,
    )
    
    fig_dual.add_trace(
        go.Scatter(
            x=df_ano_metricas['Ano'], y=df_ano_metricas['KM_Medio'],
            name="KM Médio", mode='lines+markers',
            line=dict(shape='spline', width=3, color='#10b981'),
            marker=dict(size=8)
        ),
        secondary_y=True,
    )
    
    fig_dual.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", 
        plot_bgcolor="rgba(0,0,0,0)",
        hovermode="x unified",
        font_color="#ffffff",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(t=30, b=10)
    )
    
    fig_dual.update_yaxes(title_text="Volume (Unidades)", secondary_y=False, showgrid=False, color='#3b82f6')
    fig_dual.update_yaxes(title_text="KM Médio", secondary_y=True, showgrid=False, color='#10b981')
    fig_dual.update_xaxes(showgrid=False)
    
    st.plotly_chart(fig_dual, use_container_width=True)

st.markdown("<br>", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# Matriz de Dados Base
# -----------------------------------------------------------------------------
st.markdown("#### 📋 Matriz de Auditoria Consolidada")
if not df_filtrado.empty:
    df_table = df_filtrado[["Titulo", "Preco", "Ano", "KM", "Combustivel", "Municipio", "Opcionais"]].copy()
    df_table["Preco"] = df_table["Preco"].apply(lambda x: f"R$ {x:,.0f}".replace(",", "."))
    st.dataframe(df_table, use_container_width=True, hide_index=True)