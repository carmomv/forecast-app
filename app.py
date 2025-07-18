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

if historical_file and transition_file:
    df_hist = pd.read_csv(historical_file)
    df_trans = pd.read_csv(transition_file)

    df_hist["ds"] = pd.to_datetime(df_hist["ds"])
    last_date = df_hist["ds"].max()

    df_trans.columns = [col.strip().lower() for col in df_trans.columns]
    trans_map = dict(zip(df_trans[df_trans["old/new?"] == "NEW"]["sku_old"], df_trans[df_trans["old/new?"] == "NEW"]["sku_new"]))
    df_hist["sku_virtual"] = df_hist.apply(lambda row: trans_map.get(row["sku"], row["sku"]), axis=1)
    df_hist["key"] = df_hist["sku_virtual"] + "|" + df_hist["channel"]

    df_hist["weighted_sales"] = df_hist["y"] * df_hist["availability"]
    df_hist["ano_mes"] = df_hist["ds"].dt.to_period("M")
    last_3 = df_hist[df_hist["ds"] >= last_date - pd.DateOffset(months=3)]
    baseline_sku = last_3.groupby("key").agg(avg_sales_L3M=("y", "mean"),
                                              avg_availability=("availability", "mean"),
                                              avg_weighted_sales=("weighted_sales", "mean")).reset_index()

    df_meta = df_hist.drop_duplicates("key")[["sku", "sku_virtual", "channel", "category", "brand", "key"]]
    df_base = df_meta.merge(baseline_sku, on="key", how="left")
    df_base = df_base.fillna(0)

    cat_total = df_base.groupby("category")["avg_weighted_sales"].sum().reset_index()
    cat_total.columns = ["category", "total_cat"]
    df_base = df_base.merge(cat_total, on="category", how="left")
    df_base["baseline_sku"] = df_base["avg_weighted_sales"] / df_base["total_cat"] * 18222.38333

    saz_raw = df_hist.groupby(["category", "ano_mes"])["weighted_sales"].sum().reset_index()
    media_cat = saz_raw.groupby("category")["weighted_sales"].mean().reset_index()
    media_cat.columns = ["category", "media_mensal_categoria"]
    saz = saz_raw.merge(media_cat, on="category")
    saz["fator_sazonalidade"] = saz["weighted_sales"] / saz["media_mensal_categoria"]
    saz["mes"] = saz["ano_mes"].dt.month
    saz_final = saz.groupby(["category", "mes"])["fator_sazonalidade"].mean().reset_index()
    saz_final["fator_sazonalidade"] = saz_final["fator_sazonalidade"].apply(lambda x: max(x, 0.7))

    forecast_months = pd.date_range(start=last_date + pd.offsets.MonthBegin(), periods=13, freq='MS')
    forecasts = []
    for _, row in df_base.iterrows():
        for m in forecast_months:
            fator = saz_final.loc[(saz_final["category"] == row["category"]) & (saz_final["mes"] == m.month), "fator_sazonalidade"].values
            fator = fator[0] if len(fator) > 0 else 0.7
            yhat = row["baseline_sku"] * fator
            forecasts.append({"ds": m, "sku": row["sku"], "sku_virtual": row["sku_virtual"], "channel": row["channel"],
                              "category": row["category"], "brand": row["brand"], "forecast_units": yhat})
    forecast_df = pd.DataFrame(forecasts)

    forecast_df["forecast_smooth"] = forecast_df.groupby("sku_virtual")["forecast_units"].transform(lambda x: x.rolling(3, min_periods=1).mean())

    df_trans = df_trans.dropna(subset=["date_out", "date_in"])
    df_trans["date_out"] = pd.to_datetime(df_trans["date_out"], errors="coerce")
    df_trans["date_in"] = pd.to_datetime(df_trans["date_in"], errors="coerce")
    forecast_df = forecast_df.merge(df_trans, left_on="sku", right_on="sku_old", how="left")
    forecast_df = forecast_df.merge(df_trans, left_on="sku", right_on="sku_new", how="left", suffixes=("_old", "_new"))
    forecast_df["forecast_units"] = forecast_df.apply(lambda r: 0 if (pd.notna(r["date_out_old"]) and r["ds"] >= r["date_out_old"]) else r["forecast_units"], axis=1)
    forecast_df["forecast_units"] = forecast_df.apply(lambda r: 0 if (pd.notna(r["date_in_new"]) and r["ds"] < r["date_in_new"]) else r["forecast_units"], axis=1)
    forecast_df["forecast_smooth"] = forecast_df.apply(lambda r: 0 if r["forecast_units"] == 0 else r["forecast_smooth"], axis=1)

    st.subheader("Final Forecast Preview")
    st.dataframe(forecast_df.head())

    df_hist_totals = df_hist.groupby(df_hist["ds"].dt.to_period("M"))["y"].sum().reset_index()
    df_hist_totals.columns = ["ds", "historical_units"]
    df_hist_totals["ds"] = df_hist_totals["ds"].dt.to_timestamp()

    forecast_monthly = forecast_df.groupby(forecast_df["ds"].dt.to_period("M"))[["forecast_units", "forecast_smooth"]].sum().reset_index()
    forecast_monthly["ds"] = forecast_monthly["ds"].dt.to_timestamp()
    total_combined = pd.merge(df_hist_totals, forecast_monthly, on="ds", how="outer").fillna(0).sort_values("ds")

    with st.expander("📈 Total Units per Month (Historical + Forecast)", expanded=True):
        fig = px.line(total_combined, x="ds", y=["historical_units", "forecast_units", "forecast_smooth"], markers=True,
                      title="Historical and Forecast Units per Month")
        fig.update_traces(mode="lines+markers+text", texttemplate='%{y:.0f}', textposition="top center")
        st.plotly_chart(fig, use_container_width=True)

    with st.expander("📊 Table: Monthly Totals", expanded=False):
        st.dataframe(total_combined.rename(columns={"ds": "Month"}))

    with st.expander("📊 Table: Forecast by Category", expanded=False):
        st.dataframe(forecast_df.groupby("category")[["forecast_units", "forecast_smooth"]].sum().reset_index())

    with st.expander("📊 Table: Forecast by Brand", expanded=False):
        st.dataframe(forecast_df.groupby("brand")[["forecast_units", "forecast_smooth"]].sum().reset_index())

    st.subheader("📥 Download Final Forecast")
    st.download_button(
        label="Download CSV",
        data=forecast_df.to_csv(index=False),
        file_name="Forecast_Final.csv",
        mime="text/csv"
    )
else:
    st.info("Please upload both historical sales and transition files in the sidebar to begin.")
