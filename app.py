import streamlit as st
import pandas as pd
import plotly.express as px

# === CONFIG ===
st.set_page_config(page_title="Forecast Tool", layout="wide")

# === STYLE ===
st.markdown("""
    <style>
        body {
            font-family: 'Segoe UI', sans-serif;
        }
        .title {
            text-align: center;
            font-size: 32px;
            font-weight: 600;
            color: #003057;
            margin-top: -30px;
        }
        .subtitle {
            text-align: center;
            font-size: 18px;
            color: #555;
            margin-bottom: 40px;
        }
        .block-container {
            padding-top: 2rem;
        }
        hr {
            margin: 2rem 0;
        }
    </style>
""", unsafe_allow_html=True)

# === LOGO & HEADER ===
st.image("https://upload.wikimedia.org/wikipedia/commons/2/2c/Whirlpool_logo_2022.svg", width=180)
st.markdown('<div class="title">Forecast Generator</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">Visualize and export forecast data by SKU, channel, and date</div>', unsafe_allow_html=True)

# === FILE UPLOADS ===
st.sidebar.header("Upload Files")
baseline_file = st.sidebar.file_uploader("Upload Baseline CSV", type="csv")
forecast_file = st.sidebar.file_uploader("Upload Forecast CSV", type="csv")

if baseline_file and forecast_file:
    baseline = pd.read_csv(baseline_file)
    forecast = pd.read_csv(forecast_file)

    st.markdown("### Baseline Preview")
    st.dataframe(baseline.head(), use_container_width=True)

    st.markdown("---")

    st.markdown("### Forecast Preview")
    st.dataframe(forecast.head(), use_container_width=True)

    # === FILTER ===
    sku_filter = st.multiselect("Filter by SKU", forecast["sku_virtual"].unique())
    if sku_filter:
        forecast = forecast[forecast["sku_virtual"].isin(sku_filter)]

    # === LINE CHART ===
    st.markdown("---")
    st.markdown("### Forecast vs Smoothed")
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

    # === DOWNLOAD ===
    st.markdown("---")
    st.markdown("### Export Forecast")
    st.download_button(
        label="Download Final Forecast CSV",
        data=forecast.to_csv(index=False),
        file_name="Forecast_Final.csv",
        mime="text/csv"
    )
else:
    st.info("Please upload both baseline and forecast files in the sidebar to begin.")
