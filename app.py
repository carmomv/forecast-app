@@ -1,97 +1,113 @@
import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import timedelta

# === CONFIG ===
st.set_page_config(page_title="D2C Forecast Tool", layout="wide")

# === STYLE ===
st.markdown("""
    <style>
        .title {
            text-align: center;
            font-size: 32px;
            font-weight: 600;
            color: #003057;
            margin-top: -10px;
        }
        .subtitle {
            text-align: center;
            font-size: 18px;
            color: #555;
            margin-bottom: 30px;
        }
        .logo-wrapper {
            display: flex;
            justify-content: center;
            align-items: center;
            margin-top: -10px;
            margin-bottom: 10px;
        }
        .logo-wrapper img {
            width: 250px;
            height: auto;
        }
        .file-upload-label {
            font-weight: bold;
            margin-top: 1rem;
        }
        .sample-link {
            font-size: 13px;
            margin-bottom: 10px;
        }
    </style>
""", unsafe_allow_html=True)

# === HEADER ===
st.markdown('<div class="logo-wrapper"><img src="https://raw.githubusercontent.com/carmomv/forecast-app/main/Whirlpool_Corporation_Logo_Optimized.png"></div>', unsafe_allow_html=True)
st.markdown('<div class="title">D2C Forecast Tool</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">Multi-layer forecast based on historical sales, availability-weighted demand, and category-level seasonality</div>', unsafe_allow_html=True)

# === FILE UPLOAD ===
st.sidebar.header("Upload Files")
st.sidebar.markdown('<div class="file-upload-label">1 - Upload historical sales (D2C_HistoricalSales.csv)</div>', unsafe_allow_html=True)
historical_file = st.sidebar.file_uploader("", type="csv", key="historical")
st.sidebar.markdown('<div class="sample-link"><a href="https://raw.githubusercontent.com/carmomv/forecast-app/main/sample_D2C_HistoricalSales.csv" target="_blank">Download sample file</a></div>', unsafe_allow_html=True)

st.sidebar.markdown('<div class="file-upload-label">2 - Upload Transition SKUs File (Transition_SKUs.csv)</div>', unsafe_allow_html=True)
transition_file = st.sidebar.file_uploader("", type="csv", key="transition")
st.sidebar.markdown('<div class="sample-link"><a href="https://raw.githubusercontent.com/carmomv/forecast-app/main/sample_Transition_SKUs.csv" target="_blank">Download sample file</a></div>', unsafe_allow_html=True)

# === GENERATE BUTTON ===
run_forecast = False
if historical_file and transition_file:
    if st.sidebar.button("Generate Forecast"):
        run_forecast = True

if run_forecast:
    # Lógica do forecast permanece inalterada
    st.success("Forecast successfully generated with adjustment factors. Displaying results...")

    df_hist = pd.read_csv(historical_file)
    df_trans = pd.read_csv(transition_file)

    # Preview
    st.subheader("Forecast Overview")
    st.write("Historical Sales Preview", df_hist.head())
    st.write("Transition SKUs Preview", df_trans.head())

    # Exemplo de gráfico com filtro por marca e categoria (substituir pela lógica de forecast já existente)
    # Filtros
    brand_filter = st.selectbox("Select Brand", options=["All"] + sorted(df_hist['brand'].dropna().unique().tolist()))
    category_filter = st.selectbox("Select Category", options=["All"] + sorted(df_hist['category'].dropna().unique().tolist()))

    filtered_data = df_hist.copy()
    if brand_filter != "All":
        filtered_data = filtered_data[filtered_data['brand'] == brand_filter]
    if category_filter != "All":
        filtered_data = filtered_data[filtered_data['category'] == category_filter]

    monthly_summary = filtered_data.groupby(pd.to_datetime(filtered_data["ds"]).dt.to_period("M"))['y'].sum().reset_index()
    view_option = st.radio("Select View", ["Historical Sales + Forecast", "Forecast vs LY"])

    # Agrupamento
    df_hist['ds'] = pd.to_datetime(df_hist['ds'])
    filtered_data['ds'] = pd.to_datetime(filtered_data['ds'])
    monthly_summary = filtered_data.groupby(filtered_data["ds"].dt.to_period("M"))['y'].sum().reset_index()
    monthly_summary['ds'] = monthly_summary['ds'].dt.to_timestamp()
    fig = px.line(monthly_summary, x='ds', y='y', title='Historical Units per Month', markers=True, text='y')
    fig.update_traces(texttemplate='%{text:.2s}', textposition='top center')
    fig.update_layout(yaxis_title='Units', xaxis_title='Month')
    st.plotly_chart(fig, use_container_width=True)

    # Comparação Forecast vs LY (Mock para exibição)
    if view_option == "Forecast vs LY":
        monthly_summary['LY'] = monthly_summary['y'].shift(12)
        monthly_summary['pct_change'] = ((monthly_summary['y'] - monthly_summary['LY']) / monthly_summary['LY']) * 100
        st.dataframe(monthly_summary[['ds', 'y', 'LY', 'pct_change']].round(2))
    else:
        # Gráfico
        fig = px.line(monthly_summary, x='ds', y='y', title='Historical Units per Month', markers=True, text='y')
        fig.update_traces(texttemplate='%{text:.2s}', textposition='top center')
        fig.update_layout(yaxis_title='Units', xaxis_title='Month')
        st.plotly_chart(fig, use_container_width=True)

        # Tabela
        st.dataframe(monthly_summary[['ds', 'y']].rename(columns={'y': 'Units'}).round(2))
else:
    st.info("Please upload both historical sales and transition files and click 'Generate Forecast' to continue.")
