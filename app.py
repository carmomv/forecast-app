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
            margin-top: -10px;
            margin-bottom: 10px;
        }
        .block-container {
            padding-top: 2rem;
        }
        .css-1d391kg .css-1offfwp {
            width: 350px;
        }
        hr {
            margin: 2rem 0;
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

# === LOGO E TÍTULO ===
st.markdown('<div class="logo-wrapper"><img src="https://raw.githubusercontent.com/carmomv/forecast-app/main/Whirlpool_Corporation_Logo_2017.png" width="200"></div>', unsafe_allow_html=True)
st.markdown('<div class="title">D2C Forecast Tool</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="subtitle">Multi-layer forecast based on historical sales, availability-weighted demand, and category-level seasonality</div>',
    unsafe_allow_html=True
)

# === UPLOAD ===
st.sidebar.header("Upload Files")
st.sidebar.markdown('<div class="file-upload-label">1 - Upload historical sales (D2C_HistoricalSales.csv)</div>', unsafe_allow_html=True)
historical_file = st.sidebar.file_uploader("", type="csv", key="historical")
st.sidebar.markdown('<div class="sample-link"><a href="https://raw.githubusercontent.com/carmomv/forecast-app/main/sample_D2C_HistoricalSales.csv" target="_blank">Download sample file</a></div>', unsafe_allow_html=True)

st.sidebar.markdown('<div class="file-upload-label">2 - Upload Transition SKUs File (Transition_SKUs.csv)</div>', unsafe_allow_html=True)
transition_file = st.sidebar.file_uploader("", type="csv", key="transition")
st.sidebar.markdown('<div class="sample-link"><a href="https://raw.githubusercontent.com/carmomv/forecast-app/main/sample_Transition_SKUs.csv" target="_blank">Download sample file</a></div>', unsafe_allow_html=True)

if historical_file and transition_file:
    historical = pd.read_csv(historical_file)
    transition = pd.read_csv(transition_file)

    st.subheader("Historical Sales Preview")
    st.dataframe(historical.head())

    st.subheader("Transition SKUs Preview")
    st.dataframe(transition.head())

    # Filter
    sku_filter = st.multiselect("Filter by SKU", historical["sku"].unique())
    if sku_filter:
        historical = historical[historical["sku"].isin(sku_filter)]

    # Line Chart
    st.subheader("Forecast vs Smoothed Forecast")
    if "yhat" in historical.columns and "yhat_suavizado" in historical.columns:
        forecast_melted = historical.melt(
            id_vars=["sku", "ds"], 
            value_vars=["yhat", "yhat_suavizado"], 
            var_name="Forecast Type", 
            value_name="Value"
        )

        fig = px.line(
            forecast_melted, x="ds", y="Value", color="Forecast Type",
            line_dash="Forecast Type", facet_row="sku", height=600
        )
        st.plotly_chart(fig, use_container_width=True)

    # Download
    st.subheader("\U0001F4E6 Download Final Forecast")
    st.download_button(
        label="Download CSV",
        data=historical.to_csv(index=False),
        file_name="Forecast_Final.csv",
        mime="text/csv"
    )
else:
    st.info("Please upload both historical sales and transition files in the sidebar to begin.")
