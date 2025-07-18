import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import timedelta
import datetime
from io import BytesIO

st.set_page_config(page_title="D2C Forecast Tool", layout="wide")

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
        div.stButton > button:first-child {
            background-color: #003057;
            color: white;
            font-weight: bold;
        }
    </style>
""", unsafe_allow_html=True)

st.markdown(
    '<div class="logo-wrapper">'
    '<img src="https://upload.wikimedia.org/wikipedia/commons/thumb/9/95/Whirlpool_Corporation_Logo_%28as_of_2017%29.svg/500px-Whirlpool_Corporation_Logo_%28as_of_2017%29.svg.png" '
    'alt="Whirlpool Logo" style="width:250px; height:auto;">'
    '</div>',
    unsafe_allow_html=True
)

st.markdown('<div class="title">D2C Forecast Tool</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">Multi-layer forecast based on historical sales, availability-weighted demand, and category-level seasonality</div>', unsafe_allow_html=True)

st.sidebar.header("Upload Files")
historical_file = st.sidebar.file_uploader("Upload historical sales file", type=["csv"])
transition_file = st.sidebar.file_uploader("Upload transition file", type=["csv"])
sku_list_file = st.sidebar.file_uploader("Optional: Upload CSV with SKUs for custom forecast", type=["csv"])

def style_table(df):
    now = datetime.datetime.now()
    current_month = now.strftime("%Y-%m")

    def highlight_cells(row):
        styles = []
        for col in row.index:
            if col == "Total":
                styles.append("font-weight: bold")
            else:
                if col < current_month:
                    styles.append("background-color: #eeeeee")
                else:
                    styles.append("background-color: #c6def8")
        return styles

    styled = df.style.apply(highlight_cells, axis=1)\
                     .set_table_styles([{'selector': 'th', 'props': [('font-weight', 'bold')]}])\
                     .set_properties(**{'font-weight': 'bold'}, subset=pd.IndexSlice["Total", :])\
                     .format(precision=0)
    return styled

def to_excel(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=True, sheet_name='Sheet1')
        worksheet = writer.sheets['Sheet1']
        for idx, col in enumerate(df):
            series = df[col]
            max_len = max((
                series.astype(str).map(len).max(),
                len(str(series.name))
            )) + 2
            worksheet.set_column(idx, idx, max_len)
    processed_data = output.getvalue()
    return processed_data

def prepare_export(df_hist, df_forecast, forecast_type):
    hist_pivot = df_hist.pivot_table(index=["sku_virtual", "category", "brand"], 
                                     columns=df_hist["ds"].dt.strftime("%Y-%m"),
                                     values="y", aggfunc="sum", fill_value=0)
    forecast_pivot = df_forecast.pivot_table(index=["sku", "category", "brand"], 
                                            columns=df_forecast["ds"].dt.strftime("%Y-%m"),
                                            values=forecast_type, aggfunc="sum", fill_value=0)

    hist_pivot.index.rename(["sku", "category", "brand"], inplace=True)
    combined = pd.concat([hist_pivot, forecast_pivot], axis=1, sort=False).fillna(0)
    combined = combined.reindex(sorted(combined.columns), axis=1)
    return combined

def generate_forecast(raw_hist, df_trans, selected_brands, selected_categories):
    df_hist = raw_hist.copy()
    if selected_brands:
        df_hist = df_hist[df_hist["brand"].isin(selected_brands)]
    if selected_categories:
        df_hist = df_hist[df_hist["category"].isin(selected_categories)]

    df_hist["ds"] = pd.to_datetime(df_hist["ds"])
    df_trans.columns = [col.strip().lower() for col in df_trans.columns]
    trans_map = dict(zip(df_trans[df_trans["old/new?"] == "NEW"]["sku_old"], df_trans[df_trans["old/new?"] == "NEW"]["sku_new"]))
    df_hist["sku_virtual"] = df_hist.apply(lambda row: trans_map.get(row["sku"], row["sku"]), axis=1)
    df_hist["key"] = df_hist["sku_virtual"] + "|" + df_hist["channel"]

    df_hist["weighted_sales"] = df_hist["y"] * df_hist["availability"]
    df_hist["ano_mes"] = df_hist["ds"].dt.to_period("M")
    last_date = df_hist["ds"].max()

    last_3_months = df_hist[df_hist["ds"] >= last_date - pd.DateOffset(months=3)]
    base_cat = last_3_months.groupby("category")["weighted_sales"].sum().reset_index()
    base_cat["baseline_mensal_categoria"] = base_cat["weighted_sales"] / 3

    baseline_sku = last_3_months.groupby("key").agg(avg_sales_L3M=("y", "mean"),
                                                    avg_availability=("availability", "mean"),
                                                    avg_weighted_sales=("weighted_sales", "mean")).reset_index()

    df_meta = df_hist.drop_duplicates("key")[["sku", "sku_virtual", "channel", "category", "brand", "key"]]
    df_base = df_meta.merge(baseline_sku, on="key", how="left").fillna(0)

    cat_total = df_base.groupby("category")["avg_weighted_sales"].sum().reset_index().rename(columns={"avg_weighted_sales": "total_cat"})
    df_base = df_base.merge(cat_total, on="category", how="left")
    df_base = df_base.merge(base_cat[["category", "baseline_mensal_categoria"]], on="category", how="left")
    df_base["baseline_sku"] = df_base["avg_weighted_sales"] / df_base["total_cat"] * df_base["baseline_mensal_categoria"]

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
            forecasts.append({
                "ds": m,
                "sku": row["sku"],
                "sku_virtual": row["sku_virtual"],
                "channel": row["channel"],
                "category": row["category"],
                "brand": row["brand"],
                "forecast_units": yhat
            })

    df_forecast = pd.DataFrame(forecasts)
    df_forecast["forecast_smooth"] = df_forecast.sort_values(by=["sku_virtual", "channel", "ds"]).groupby(["sku_virtual", "channel"])["forecast_units"].transform(lambda x: x.rolling(3, min_periods=1, center=True).mean())

    return df_hist, df_forecast, df_base, saz_final, base_cat

def forecast_for_new_skus(sku_list, df_hist, df_forecast, df_base, saz_final, base_cat):
    existing_skus = set(df_hist["sku"].unique()).union(set(df_forecast["sku"].unique()))

    sku_list = sku_list.drop_duplicates(subset=["sku"])
    sku_list["sku"] = sku_list["sku"].astype(str)
    new_skus = sku_list[~sku_list["sku"].isin(existing_skus)]

    if new_skus.empty:
        return pd.DataFrame(), []

    if not {"category", "brand"}.issubset(new_skus.columns):
        mapping = df_base[["sku", "category", "brand"]].drop_duplicates()
        new_skus = new_skus.merge(mapping, on="sku", how="left")

    forecast_months = pd.date_range(start=df_hist["ds"].max() + pd.offsets.MonthBegin(), periods=13, freq='MS')

    forecasts_new = []
    for _, row in new_skus.iterrows():
        cat = row["category"]
        brand = row["brand"]
        sku = row["sku"]
        if pd.isna(cat) or pd.isna(brand):
            continue

        base_cat_val = base_cat[(base_cat["category"] == cat)]
        if base_cat_val.empty:
            continue

        base_val = base_cat_val["baseline_mensal_categoria"].values[0]

        for m in forecast_months:
            mes_num = m.month
            saz_factor = saz_final[(saz_final["category"] == cat) & (saz_final["mes"] == mes_num)]["fator_sazonalidade"]
            saz_factor = saz_factor.values[0] if not saz_factor.empty else 0.7
            yhat = base_val * saz_factor
            forecasts_new.append({
                "ds": m,
                "sku": sku,
                "sku_virtual": sku,
                "channel": "Unknown",
                "category": cat,
                "brand": brand,
                "forecast_units": yhat
            })

    df_forecast_new = pd.DataFrame(forecasts_new)
    if not df_forecast_new.empty:
        df_forecast_new["forecast_smooth"] = df_forecast_new.sort_values(by=["sku_virtual", "channel", "ds"]).groupby(["sku_virtual", "channel"])["forecast_units"].transform(lambda x: x.rolling(3, min_periods=1, center=True).mean())

    return df_forecast_new, new_skus["sku"].tolist()

# MAIN FLOW com session_state

if historical_file and transition_file:
    raw_hist = pd.read_csv(historical_file)
    df_trans = pd.read_csv(transition_file)

    with st.sidebar:
        selected_brands = st.multiselect("Select brands to include in forecast:", options=raw_hist["brand"].dropna().unique())
        selected_categories = st.multiselect("Select categories to include in forecast:", options=raw_hist["category"].dropna().unique())
        generate_btn = st.button("Generate Forecast", help="Click to generate forecast", key="gen_btn")

    if generate_btn or "df_all" in st.session_state:
        if generate_btn:
            df_hist, df_forecast, df_base, saz_final, base_cat = generate_forecast(raw_hist, df_trans, selected_brands, selected_categories)

            if sku_list_file is not None:
                sku_list = pd.read_csv(sku_list_file)
                sku_list.columns = [c.lower() for c in sku_list.columns]
                if "sku" not in sku_list.columns:
                    st.error("Arquivo SKU customizado deve conter coluna 'sku'")
                else:
                    df_forecast_new, skus_novos = forecast_for_new_skus(sku_list, df_hist, df_forecast, df_base, saz_final, base_cat)
                    if not df_forecast_new.empty:
                        df_forecast = pd.concat([df_forecast, df_forecast_new], ignore_index=True)
                        st.info(f"Forecast gerado para SKUs novos: {skus_novos}")
                    else:
                        st.info("Nenhum SKU novo identificado para forecast customizado.")

            df_all = pd.concat([
                df_hist[["ds", "sku_virtual", "brand", "category", "channel", "y"]].rename(columns={"sku_virtual": "sku"}),
                df_forecast[["ds", "sku", "brand", "category", "channel", "forecast_units", "forecast_smooth"]]
            ], ignore_index=True)

            st.session_state["df_all"] = df_all
            st.session_state["df_hist"] = df_hist
            st.session_state["df_forecast"] = df_forecast
            st.session_state["forecast_col_map"] = {
                "Base Forecast": "forecast_units",
                "Optimized Forecast": "forecast_smooth"
            }

        # Carrega os dados do estado da sessão
        df_all = st.session_state["df_all"]
        df_hist = st.session_state["df_hist"]
        df_forecast = st.session_state["df_forecast"]
        forecast_col_map = st.session_state["forecast_col_map"]

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            brand_filter = st.multiselect("Select Brand(s):", options=df_all["brand"].dropna().unique())
        with col2:
            category_filter = st.multiselect("Select Category(ies):", options=df_all["category"].dropna().unique())
        with col3:
            sku_filter = st.multiselect("Select SKU(s):", options=df_all["sku"].dropna().unique())
        with col4:
            channel_filter = st.multiselect("Select Channel(s):", options=df_all["channel"].dropna().unique())

        df_plot = df_all.copy()
        if brand_filter:
            df_plot = df_plot[df_plot["brand"].isin(brand_filter)]
        if category_filter:
            df_plot = df_plot[df_plot["category"].isin(category_filter)]
        if sku_filter:
            df_plot = df_plot[df_plot["sku"].isin(sku_filter)]
        if channel_filter:
            df_plot = df_plot[df_plot["channel"].isin(channel_filter)]

        summary = df_plot.groupby("ds")[["y", "forecast_units", "forecast_smooth"]].sum().reset_index()

        fig = px.line(summary, x="ds", y=["y", "forecast_units", "forecast_smooth"],
                      labels={"value": "Units", "ds": "Date", "variable": "Type"},
                      title="Historical and Forecasted Sales",
                      color_discrete_sequence=["#003057", "#FDB913", "#4285F4"])

        for trace in fig.data:
            trace.update(mode="lines+markers+text",
                         text=[str(int(val)) for val in trace.y],
                         textposition="top center",
                         textfont=dict(weight="bold"))

        fig.update_layout(legend_title_text='Legend')
        st.plotly_chart(fig, use_container_width=True)

        forecast_choice = st.radio(
            "Select forecast type to display in tables:",
            options=["Base Forecast", "Optimized Forecast"],
            index=0,
            horizontal=True
        )

        forecast_col = forecast_col_map[forecast_choice]

        df_plot["ds_str"] = df_plot["ds"].dt.strftime("%Y-%m")
        df_plot["value"] = df_plot.apply(lambda row: row["y"] if pd.notna(row["y"]) else row[forecast_col], axis=1)
        df_pivot_cat = df_plot.pivot_table(index="category", columns="ds_str", values="value", aggfunc="sum", margins=True, margins_name="Total").fillna(0).round(0)
        df_pivot_brand = df_plot.pivot_table(index="brand", columns="ds_str", values="value", aggfunc="sum", margins=True, margins_name="Total").fillna(0).round(0)

        def style_table(df):
            now = datetime.datetime.now()
            current_month = now.strftime("%Y-%m")

            def highlight_cells(row):
                styles = []
                for col in row.index:
                    if col == "Total":
                        styles.append("font-weight: bold")
                    else:
                        if col < current_month:
                            styles.append("background-color: #eeeeee")
                        else:
                            styles.append("background-color: #c6def8")
                return styles

            styled = df.style.apply(highlight_cells, axis=1)\
                             .set_table_styles([{'selector': 'th', 'props': [('font-weight', 'bold')]}])\
                             .set_properties(**{'font-weight': 'bold'}, subset=pd.IndexSlice["Total", :])\
                             .format(precision=0)
            return styled

        st.markdown("### Forecast by Category")
        st.dataframe(style_table(df_pivot_cat))

        st.markdown("### Forecast by Brand")
        st.dataframe(style_table(df_pivot_brand))

        export_df = prepare_export(df_hist, df_forecast, forecast_col)

        towrite = BytesIO()
        with pd.ExcelWriter(towrite, engine='xlsxwriter') as writer:
            export_df.to_excel(writer, sheet_name='Forecast_History')
        towrite.seek(0)

        st.download_button(
            label="Download Excel (History + Forecast)",
            data=towrite,
            file_name="forecast_history.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key="download-btn"
        )


