import streamlit as st
import pandas as pd
import plotly.express as px
import io
from io import BytesIO
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

if historical_file and transition_file:
    df_hist = pd.read_csv(historical_file)
    df_trans = pd.read_csv(transition_file)

    st.subheader("Historical Sales Preview")
    st.dataframe(df_hist.head())

    st.subheader("Transition SKUs Preview")
    st.dataframe(df_trans.head())

    # === Pipeline Forecast (Simples) ===
    df_hist["ds"] = pd.to_datetime(df_hist["ds"])
    last_date = df_hist["ds"].max()
    forecast_months = pd.date_range(start=last_date + pd.offsets.MonthBegin(), periods=13, freq='MS')

    # SKU Virtual Mapping
    col_status = [c for c in df_trans.columns if "old" in c.lower()][0]
    trans_map = dict(zip(df_trans[df_trans[col_status] == "NEW"]["sku"], df_trans[df_trans[col_status] == "NEW"]["sku_virtual"]))
    df_hist["sku_virtual"] = df_hist.apply(lambda row: trans_map.get(row["sku"], row["sku"]), axis=1)
    df_hist["key"] = df_hist["sku_virtual"] + "|" + df_hist["channel"]
    df_hist["weighted_sales"] = df_hist["sales"] * df_hist["availability"]
    df_hist["month"] = df_hist["ds"].dt.to_period("M")

    # Baseline por SKU
    last_3 = df_hist[df_hist["ds"] >= last_date - pd.DateOffset(months=3)]
    baseline_df = last_3.groupby("key").agg({"weighted_sales": "mean"}).reset_index()
    baseline_df.columns = ["key", "avg_weighted_sales"]

    # Sazonalidade por categoria
    cat_month = df_hist.groupby(["category", "month"])["weighted_sales"].sum().reset_index()
    cat_avg = cat_month.groupby("category")["weighted_sales"].mean().reset_index()
    cat_avg.columns = ["category", "monthly_avg"]
    sazonalidade = pd.merge(cat_month, cat_avg, on="category")
    sazonalidade["fator"] = sazonalidade["weighted_sales"] / sazonalidade["monthly_avg"]
    sazonalidade["mes"] = sazonalidade["month"].dt.month
    saz = sazonalidade.groupby(["category", "mes"])["fator"].mean().reset_index()

    # Forecast por SKU
    df_base = df_hist.drop_duplicates("key")[["sku", "sku_virtual", "channel", "category", "brand", "key"]]
    df_base = pd.merge(df_base, baseline_df, on="key", how="left").fillna(0)
    forecasts = []
    for _, row in df_base.iterrows():
        for m in forecast_months:
            mes = m.month
            fator = saz.loc[(saz["category"] == row["category"]) & (saz["mes"] == mes), "fator"].values
            fator = max(fator[0], 0.7) if len(fator) > 0 else 0.7
            yhat = row["avg_weighted_sales"] * fator
            forecasts.append({
                "ds": m,
                "sku": row["sku"],
                "sku_virtual": row["sku_virtual"],
                "channel": row["channel"],
                "category": row["category"],
                "brand": row["brand"],
                "forecast_units": yhat
            })

    forecast_df = pd.DataFrame(forecasts)

    # === Visualização ===
    st.subheader("Forecast Summary")
    forecast_df["ds"] = pd.to_datetime(forecast_df["ds"])
    total_monthly = forecast_df.groupby(forecast_df["ds"].dt.to_period("M"))["forecast_units"].sum().reset_index()
    total_monthly["ds"] = total_monthly["ds"].astype(str)
    fig = px.line(total_monthly, x="ds", y="forecast_units", title="Total Forecast per Month", markers=True)
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("Forecast Table by Month")
    st.dataframe(total_monthly.rename(columns={"ds": "Month", "forecast_units": "Forecast Units"}))

    st.subheader("Forecast Table by Category")
    st.dataframe(forecast_df.groupby("category")["forecast_units"].sum().reset_index().rename(columns={"forecast_units": "Forecast Units"}))

    st.subheader("Forecast Table by Brand")
    st.dataframe(forecast_df.groupby("brand")["forecast_units"].sum().reset_index().rename(columns={"forecast_units": "Forecast Units"}))

    # Download final
    st.subheader("\U0001F4E6 Download Final Forecast")
    st.download_button(
        label="Download CSV",
        data=forecast_df.to_csv(index=False),
        file_name="Forecast_Final.csv",
        mime="text/csv"
    )
else:
    st.info("Please upload both historical sales and transition files in the sidebar to begin.")
