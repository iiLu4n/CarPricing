from pathlib import Path
import pandas as pd
import streamlit as st

# Configuração da página do aplicativo
st.set_page_config(
    page_title="Radar de Luxo & Elétricos - Inteligência de Mercado",
    page_icon="🏎️",
    layout="wide",
)


# Função para carregar e tratar os dados de veículos com cache
@st.cache_data
def get_vehicle_data():
  # Tenta encontrar o arquivo em diferentes caminhos comuns
  caminhos_possiveis = [
      Path(__file__).parent / "data/bmw_inteligencia_mercado_completo.csv",
      Path(__file__).parent / "bmw_inteligencia_mercado_completo.csv",
      Path("bmw_inteligencia_mercado_completo.csv"),
  ]

  arquivo_encontrado = None
  for caminho in caminhos_possiveis:
    if caminho.exists():
      arquivo_encontrado = caminho
      break

  if not arquivo_encontrado:
    st.error(
        "❌ Arquivo CSV não encontrado! Certifique-se de que o arquivo"
        " 'bmw_inteligencia_mercado_completo.csv' está na raiz do projeto ou na"
        " pasta data/."
    )
    return pd.DataFrame()

  df = pd.read_csv(arquivo_encontrado)

  # Limpezas e tipagem de dados
  df = df[df["Preco"] > 0].copy()
  df["KM_Int"] = pd.to_numeric(
      df["KM"].astype(str).str.replace(r"\D", "", regex=True), errors="coerce"
  ).fillna(0)
  df["Ano"] = pd.to_numeric(df["Ano"], errors="coerce").fillna(0)

  # Cálculo do Preço Médio por Modelo para achar oportunidades (Benchmark interno)
  df["Preco_Medio_Modelo"] = df.groupby("Modelo")["Preco"].transform("mean")
  df["Desagio_Pct"] = (
      1 - (df["Preco"] / df["Preco_Medio_Modelo"])
  ) * 100

  return df


df = get_vehicle_data()

# Se o DataFrame estiver vazio, interrompe a execução para evitar erros
if df.empty:
  st.stop()

# -----------------------------------------------------------------------------
# Interface do Dashboard - Topo
# -----------------------------------------------------------------------------
st.title("🏎️ Radar de Inteligência de Mercado: Luxo & Elétricos")
st.markdown(
    "Plataforma B2B de monitoramento de assimetria de preços, geolocalização e"
    " oportunidades de arbitragem."
)
st.markdown("---")

# -----------------------------------------------------------------------------
# Barra Lateral (Filtros Avançados)
# -----------------------------------------------------------------------------
st.sidebar.header("🔍 Filtros de Mercado")

modelos_disponiveis = sorted(df["Modelo"].dropna().unique().tolist())
modelo_selecionado = st.sidebar.multiselect(
    "Modelos de Veículos",
    modelos_disponiveis,
    default=modelos_disponiveis,
)

municipios_disponiveis = sorted(df["Municipio"].dropna().unique().tolist())
municipio_selecionado = st.sidebar.multiselect(
    "Municípios / Praças",
    municipios_disponiveis,
    default=municipios_disponiveis,
)

min_ano = int(df["Ano"].min()) if df["Ano"].min() > 0 else 2020
max_ano = int(df["Ano"].max()) if df["Ano"].max() > 0 else 2026
anos_filtro = st.sidebar.slider(
    "Ano do Veículo", min_value=min_ano, max_value=max_ano, value=[min_ano, max_ano]
)

# Aplicando os filtros
df_filtrado = df[
    (df["Modelo"].isin(modelo_selecionado))
    & (df["Municipio"].isin(municipio_selecionado))
    & (df["Ano"] >= anos_filtro[0])
    & (df["Ano"] <= anos_filtro[1])
]

# -----------------------------------------------------------------------------
# Métricas Executivas (KPIs de Alto Impacto)
# -----------------------------------------------------------------------------
st.subheader("📊 Indicadores Chave de Desempenho (KPIs)")

col1, col2, col3, col4 = st.columns(4)

total_veiculos = len(df_filtrado)
preco_medio = df_filtrado["Preco"].mean() if total_veiculos > 0 else 0
oportunidades_count = len(df_filtrado[df_filtrado["Desagio_Pct"] >= 10])
bairros_atendidos = df_filtrado["Bairro"].nunique()

col1.metric("Veículos Monitorados", f"{total_veiculos} un")
col2.metric(
    "Ticket Médio da Praça",
    f"R$ {preco_medio:,.0f}".replace(",", "."),
)
col3.metric(
    "Oportunidades de Arbitragem",
    f"{oportunidades_count} carros",
    help="Anúncios com mais de 10% de deságio em relação à média do modelo.",
)
col4.metric("Micro-Regiões (Bairros)", f"{bairros_atendidos} locais")

st.markdown("---")

# -----------------------------------------------------------------------------
# Bloco 1: Alertas de Oportunidade
# -----------------------------------------------------------------------------
st.subheader("🔥 Alertas de Oportunidade de Arbitragem (Abaixo da Média)")
st.markdown(
    "Estes veículos estão anunciados significativamente abaixo da média de"
    " mercado para o mesmo modelo."
)

df_oportunidades = df_filtrado[df_filtrado["Desagio_Pct"] >= 10].sort_values(
    by="Desagio_Pct", ascending=False
)

if not df_oportunidades.empty:
  for _, row in df_oportunidades.iterrows():
    with st.container():
      c1, c2, c3, c4 = st.columns([3, 1.5, 1.5, 1])
      c1.markdown(f"**{row['Titulo']}**")
      c2.markdown(
          f"💰 **R$ {row['Preco']:,.0f}**".replace(",", ".")
          + f" *({row['Desagio_Pct']:.1f}% abaixo)*"
      )
      c3.markdown(f"📍 {row['Bairro']}, {row['Municipio']}")
      c4.markdown(f"[🔗 Ver Anúncio]({row['Link']})", unsafe_allow_html=True)
      st.divider()
else:
  st.info(
      "Nenhuma oportunidade extrema detectada com os filtros atuais. Tente"
      " expandir a seleção na barra lateral."
  )

# -----------------------------------------------------------------------------
# Bloco 2: Gráficos de Análise
# -----------------------------------------------------------------------------
col_left, col_right = st.columns(2)

with col_left:
  st.subheader("📈 Preço Médio por Modelo")
  if not df_filtrado.empty:
    df_chart = (
        df_filtrado.groupby("Modelo")["Preco"].mean().reset_index()
    )
    st.bar_chart(df_chart, x="Modelo", y="Preco", use_container_width=True)
  else:
    st.warning("Sem dados para exibir.")

with col_right:
  st.subheader("🗺️ Concentração por Município")
  if not df_filtrado.empty:
    df_mun = df_filtrado["Municipio"].value_counts().reset_index()
    df_mun.columns = ["Municipio", "Quantidade"]
    st.bar_chart(df_mun, x="Municipio", y="Quantidade", use_container_width=True)
  else:
    st.warning("Sem dados para exibir.")

st.markdown("---")

# -----------------------------------------------------------------------------
# Bloco 3: Tabela Completa
# -----------------------------------------------------------------------------
st.subheader("📋 Inventário Completo Processado")
colunas_exibicao = [
    "Titulo",
    "Preco",
    "Ano",
    "KM",
    "Cambio",
    "Combustivel",
    "Municipio",
    "Bairro",
    "UnicoDono",
    "IPVA_Pago",
    "Link",
]
st.dataframe(
    df_filtrado[colunas_exibicao], use_container_width=True, hide_index=True
)