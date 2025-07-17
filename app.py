import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Forecast App", layout="wide")
st.title("📈 Forecast Generator")

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
    st.subheader("Forecast vs Suavizado")
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
    st.subheader("📦 Download Final Forecast")
    st.download_button(
        label="Download CSV",
        data=forecast.to_csv(index=False),
        file_name="Forecast_Final.csv",
        mime="text/csv"
    )
else:
    st.info("Please upload both baseline and forecast files in the sidebar to begin.")
