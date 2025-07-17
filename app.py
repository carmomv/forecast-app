import streamlit as st
import pandas as pd
import plotly.express as px

# === CONFIG ===
st.set_page_config(page_title="D2C Forecast Tool", layout="wide")

# === STYLE ===
st.markdown("""
    <style>
        /* Sidebar styling */
        section[data-testid="stSidebar"] {
            width: 350px !important;
        }

        /* Center logo and content */
        .main-title-wrapper {
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            margin-bottom: 2rem;
            margin-top: 1rem;
        }

        .main-title-wrapper img {
            width: 160px;
            margin-bottom: 0.3rem;
        }

        .main-title {
            font-size: 32px;
            font-weight: 700;
            color: #003057;
        }

        .subtitle {
            font-size: 16px;
            color: #444;
            margin-top: 0.2rem;
            text-align: center;
            max-width: 800px;
        }

        .block-container {
            padding-top: 2rem;
        }

        .stDownloadButton > button {
            background-color: #003057;
            color: white;
            font-weight: bold;
        }
    </style>
""", unsafe_allow_html=True)

# === LOGO + TÍTULO ===
st.markdown("""
    <div class="main-title-wrapper">
        <img src="https://raw.githubusercontent.com/carmomv/forecast-app/main/Whirlpool_Corporation_Logo_(as_of_2017).svg.png">
        <div class="main-title">D2C Forecast Tool</div>
        <div class="subtitle">
            Multi-layer forecast based on historical sales, availability-weighted demand, and category-level seasonality
        </div>
    </div>
""", unsafe_allow_html=True)

# === UPLOADS ===
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

    sku_filter = st.multiselect("Filter by SKU", forecast["sku_virtual"].unique())
    if sku_filter:
        forecast = forecast[forecast["sku_virtual"].isin(sku_filter)]

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

    st.subheader("\U0001F4E6 Download Final Forecast")
    st.download_button(
        label="Download CSV",
        data=forecast.to_csv(index=False),
        file_name="Forecast_Final.csv",
        mime="text/csv"
    )
else:
    st.info("Please upload both baseline and forecast files in the sidebar to begin.")
