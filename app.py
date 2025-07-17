import streamlit as st
import pandas as pd
import plotly.express as px

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
            margin-top: -20px;
            margin-bottom: 10px;
        }
        .block-container {
            padding-top: 2rem;
        }
        .css-1d391kg .css-1offfwp {
            width: 350px; /* Aumenta a largura da barra lateral */
        }
        hr {
            margin: 2rem 0;
        }
    </style>
""", unsafe_allow_html=True)

# === LOGO E TÍTULO ===
st.markdown('<div class="logo-wrapper"><img src="https://raw.githubusercontent.com/carmomv/forecast-app/main/Whirlpool_Corporation_Logo_(as_of_2017).svg.png" width="200"></div>', unsafe_allow_html=True)
st.markdown('<div class="title">D2C Forecast Tool</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="subtitle">Multi-layer forecast based on historical sales, availability-weighted demand, and category-level seasonality</div>',
    unsafe_allow_html=True
)

# === UPLOAD ===
st.sidebar.header("Upload Files")
baseline_file = st.sidebar.file_uploader("Upload Baseline_Final_Por_SKU_Canal.csv", type="csv")
forecast_file = st.sidebar.file_uploader("Upload Forecast_Completo_Com_Baseline_e_Transicoes.csv", type="csv")

if baseline_file and forecast_file:
    baseline = pd.read_csv(baseline_file)
    forecast = pd.read_csv(forecast_file)

    st.subheader("Baseline Preview")
    st.dataframe(baseline.head())

    st.subheader("Forecast Preview")
    st.dataframe(forecast.head())

    # Filter
    sku_filter = st.multiselect("Filter by SKU", forecast["sku_virtual"].unique())
    if sku_filter:
        forecast = forecast[forecast["sku_virtual"].isin(sku_filter)]

    # Line Chart
    st.subheader("Forecast vs Smoothed Forecast")
    forecast_melted = forecast.melt(
        id_vars=["sku_virtual", "ds"], 
        value_vars=["yhat", "yhat_suavizado"], 
        var_name="Forecast Type", 
        value_name="Value"
    )

    fig = px.line(
        forecast_melted, x="ds", y="Value", color="Forecast Type",
        line_dash="Forecast Type", facet_row="sku_virtual", height=600
    )
    st.plotly_chart(fig, use_container_width=True)

    # Download
    st.subheader("\U0001F4E6 Download Final Forecast")
    st.download_button(
        label="Download CSV",
        data=forecast.to_csv(index=False),
        file_name="Forecast_Final.csv",
        mime="text/csv"
    )
else:
    st.info("Please upload both baseline and forecast files in the sidebar to begin.")
