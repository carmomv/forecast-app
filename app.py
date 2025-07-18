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
        .stButton>button {
            background-color: #007A33;
            color: white;
            font-weight: bold;
            border-radius: 5px;
            padding: 0.4em 1em;
            margin-top: 0.5em;
        }
        .stButton>button:hover {
            background-color: #005c25;
            color: white;
        }
        .stButton>button:focus {
            background-color: #007A33;
            color: white;
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
    st.success("Forecast successfully generated. Displaying results...")

    df_hist = pd.read_csv(historical_file)
    df_trans = pd.read_csv(transition_file)

    df_hist['ds'] = pd.to_datetime(df_hist['ds'])
    df_hist = df_hist[df_hist['ds'].notna() & df_hist['y'].notna()]
    df_hist = df_hist.sort_values(by='ds')

    # SKU transition
    trans_map = dict(zip(df_trans[df_trans["OLD/NEW?"] == "NEW"]["sku_old"], df_trans[df_trans["OLD/NEW?"] == "NEW"]["sku_new"]))
    df_hist['sku_virtual'] = df_hist['sku'].replace(trans_map)
    df_hist['sku_virtual'] = df_hist['sku_virtual'].fillna(df_hist['sku'])

    # Weighted sales
    df_hist['weighted_sales'] = df_hist['y'] * df_hist['availability']

    # Baseline por categoria
    last_date = df_hist['ds'].max()
    df_last_3 = df_hist[df_hist['ds'] >= (last_date - pd.DateOffset(months=3))]
    df_base_cat = df_last_3.groupby('category')['weighted_sales'].sum().reset_index()
    df_base_cat['baseline_mensal_categoria'] = df_base_cat['weighted_sales'] / 3

    # Share por SKU
    df_share = df_last_3.groupby(['sku_virtual', 'category'])['weighted_sales'].sum().reset_index()
    df_total_cat = df_share.groupby('category')['weighted_sales'].sum().reset_index().rename(columns={'weighted_sales': 'total_cat'})
    df_share = pd.merge(df_share, df_total_cat, on='category')
    df_share['share'] = df_share['weighted_sales'] / df_share['total_cat']
    df_share = pd.merge(df_share, df_base_cat[['category', 'baseline_mensal_categoria']], on='category')
    df_share['forecast_units'] = df_share['share'] * df_share['baseline_mensal_categoria']

    # Sazonalidade
    df_hist['month'] = df_hist['ds'].dt.month
    df_season = df_hist.groupby(['category', 'month'])['y'].mean().reset_index()
    df_season = df_season.groupby('category').apply(lambda x: x.set_index('month')['y'] / x['y'].mean()).reset_index()
    df_season.columns = ['category', 'month', 'seasonality']
    df_season['seasonality'] = df_season['seasonality'].apply(lambda x: max(x, 0.7))

    # Previsao final
    future_months = pd.date_range(start=last_date + pd.DateOffset(months=1), periods=13, freq='MS')
    forecast_list = []
    for _, row in df_share.iterrows():
        for date in future_months:
            month = date.month
            saz = df_season[(df_season['category'] == row['category']) & (df_season['month'] == month)]['seasonality'].values
            saz = saz[0] if len(saz) > 0 else 1.0
            forecast_list.append({
                'ds': date,
                'sku': row['sku_virtual'],
                'category': row['category'],
                'brand': df_hist[df_hist['sku_virtual'] == row['sku_virtual']]['brand'].iloc[0],
                'forecast_units': row['forecast_units'] * saz
            })

    df_forecast = pd.DataFrame(forecast_list)

    # Aplicar transições de SKU com base em data
    df_trans['date_in'] = pd.to_datetime(df_trans['date_in'], errors='coerce')
    df_trans['date_out'] = pd.to_datetime(df_trans['date_out'], errors='coerce')
    for _, row in df_trans.iterrows():
        sku = row['sku_new']
        if pd.notna(row['date_in']):
            df_forecast.loc[(df_forecast['sku'] == sku) & (df_forecast['ds'] < row['date_in']), ['forecast_units']] = 0
        if pd.notna(row['date_out']):
            df_forecast.loc[(df_forecast['sku'] == sku) & (df_forecast['ds'] > row['date_out']), ['forecast_units']] = 0

    # Forecast suavizado
    df_forecast['forecast_smooth'] = df_forecast.groupby('sku')['forecast_units'].transform(lambda x: x.rolling(3, center=True, min_periods=1).mean())

    # Concatenar historico e previsao
    df_all = pd.concat([
        df_hist[['ds', 'sku_virtual', 'brand', 'category', 'y']].rename(columns={'sku_virtual': 'sku'}),
        df_forecast[['ds', 'sku', 'brand', 'category', 'forecast_units', 'forecast_smooth']]
    ], ignore_index=True)

    # Manual adjustments
    st.sidebar.markdown("**Manual Adjustment Factors by Month**")
    month_factors = {}
    for date in future_months:
        label = date.strftime("%b %Y")
        month_factors[date] = st.sidebar.number_input(f"{label}", min_value=0.0, value=1.0, step=0.01, format="%.2f", key=label)

    apply_adj = st.sidebar.button("Run Manual Adjustments")

    if apply_adj:
        df_forecast['adjustment'] = df_forecast['ds'].map(month_factors).fillna(1.0)
        df_forecast['forecast_units'] *= df_forecast['adjustment']
        df_forecast['forecast_smooth'] *= df_forecast['adjustment']
        df_all.update(df_forecast[['ds', 'sku', 'forecast_units', 'forecast_smooth']])

    # Filtros visuais
    st.subheader("Visualizations")
    brand_filter = st.selectbox("Select Brand", options=["All"] + sorted(df_all['brand'].dropna().unique()))
    category_filter = st.selectbox("Select Category", options=["All"] + sorted(df_all['category'].dropna().unique()))

    df_plot = df_all.copy()
    if brand_filter != "All":
        df_plot = df_plot[df_plot['brand'] == brand_filter]
    if category_filter != "All":
        df_plot = df_plot[df_plot['category'] == category_filter]

    summary = df_plot.groupby('ds').agg({
        'y': 'sum',
        'forecast_units': 'sum',
        'forecast_smooth': 'sum'
    }).reset_index()

    fig = px.line(summary, x='ds', y=['y', 'forecast_units', 'forecast_smooth'],
                  labels={'value': 'Units', 'ds': 'Date', 'variable': 'Type'},
                  title='Historical and Forecasted Sales')
    fig.update_layout(legend_title_text='Legend')
    st.plotly_chart(fig, use_container_width=True)

    st.dataframe(summary.round(2))

else:
    st.info("Please upload both historical sales and transition files and click 'Generate Forecast' to continue.")
