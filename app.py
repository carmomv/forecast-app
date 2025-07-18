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

    # Filtros
    brand_filter = st.selectbox("Select Brand", options=["All"] + sorted(df_hist['brand'].dropna().unique().tolist()))
    category_filter = st.selectbox("Select Category", options=["All"] + sorted(df_hist['category'].dropna().unique().tolist()))

    filtered_data = df_hist.copy()
    if brand_filter != "All":
        filtered_data = filtered_data[filtered_data['brand'] == brand_filter]
    if category_filter != "All":
        filtered_data = filtered_data[filtered_data['category'] == category_filter]

    # Campo para ajuste manual por mês
    st.markdown("**Manual Adjustment Factors by Month**")
    filtered_data['ds'] = pd.to_datetime(filtered_data['ds'])
    future_months = sorted(filtered_data[filtered_data['ds'] > filtered_data['ds'].max() - pd.DateOffset(months=13)]['ds'].dt.to_period("M").unique().to_timestamp())

    adjustment_factors = {}
    for month in future_months:
        month_str = month.strftime("%b %Y")
        factor = st.number_input(f"Adjustment factor for {month_str}", min_value=0.0, value=1.0, step=0.01, format="%.2f")
        adjustment_factors[month] = factor

    # Aplicar os fatores manuais ao dataset
    filtered_data['adjustment_factor'] = filtered_data['ds'].dt.to_period("M").dt.to_timestamp().map(adjustment_factors).fillna(1.0)
    filtered_data['adjusted_y'] = filtered_data['y'] * filtered_data['adjustment_factor']

    # Agrupamento
    monthly_summary = filtered_data.groupby(filtered_data["ds"].dt.to_period("M"))['adjusted_y'].sum().reset_index()
    monthly_summary['ds'] = monthly_summary['ds'].dt.to_timestamp()

    # Gráfico
    fig = px.line(monthly_summary, x='ds', y='adjusted_y', title='Historical + Forecast Units per Month (Adjusted)', markers=True, text='adjusted_y')
    fig.update_traces(texttemplate='%{text:.2f}', textposition='top center')
    fig.update_layout(yaxis_title='Units', xaxis_title='Month')
    st.plotly_chart(fig, use_container_width=True)

    # Tabela
    st.dataframe(monthly_summary[['ds', 'adjusted_y']].rename(columns={'adjusted_y': 'Units'}).round(2))
else:
    st.info("Please upload both historical sales and transition files and click 'Generate Forecast' to continue.")
