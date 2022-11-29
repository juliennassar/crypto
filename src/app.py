from datetime import date, datetime, timedelta
from io import StringIO

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
import streamlit as st

from data_api import compute_investment_stats, get_avg_price_for_symbol, get_hist_klines, symbol_prices
from db import get_trades

st.set_page_config(
    page_title="cryptolit",
    page_icon="./assets/bitcoin.png",
    layout="wide",
)

EURBUSD_symbol = "EURBUSD"
EURBUSD_rate = get_avg_price_for_symbol(EURBUSD_symbol)
trades = get_trades()
investment_stats_df = compute_investment_stats(df=trades)
symbol_list = list(set(trades["symbol"].values))
current_prices = symbol_prices(symbol_list)

# with st.sidebar:
#     currency = st.radio(
#         label="currency",
#         options=["USD", "EUR"],
#     )
#     symbol_filter = st.multiselect("symbol", symbol_list, default=["BTCBUSD", "ETHBUSD"])

summary = (
    investment_stats_df[investment_stats_df["symbol"] != EURBUSD_symbol]
    .groupby("symbol")
    .agg({"average_buy_price": "last", "holding": "last", "realized_gains": "sum"})
    .join(current_prices)
)
summary["value"] = summary.price * summary.holding
summary["invested"] = summary.average_buy_price * summary.holding
summary["pnl"] = summary.value - summary.invested

st.title("Crypto dashboard")

# display = compute_investment(trades)

st.header("Invested")

euros_invested = sum(
    investment_stats_df[
        (investment_stats_df["symbol"] == EURBUSD_symbol) & (investment_stats_df["is_buyer"] == 0)
    ].quantity
) - sum(
    investment_stats_df[
        (investment_stats_df["symbol"] == EURBUSD_symbol) & (investment_stats_df["is_buyer"] == 1)
    ].quantity
)
usd_invested = round(
    sum(
        investment_stats_df[
            (investment_stats_df["symbol"] == EURBUSD_symbol) & (investment_stats_df["is_buyer"] == 0)
        ].quote_quantity
    )
    - sum(
        investment_stats_df[
            (investment_stats_df["symbol"] == EURBUSD_symbol) & (investment_stats_df["is_buyer"] == 1)
        ].quote_quantity
    ),
    0,
)

st.text(f"Invested EUR {euros_invested:.2f}")
col1, col2 = st.columns(2)
with col1:
    portfolio_value = sum(summary.holding * summary.price)
    st.metric(
        label=f"Investment USD {usd_invested:.2f}",
        value=round(portfolio_value, 2),
        delta=round(portfolio_value - usd_invested, 2),
    )
with col2:
    USD_purchase_price = usd_invested / euros_invested
    st.metric(
        label=f"EUR/BUSD {USD_purchase_price:.3f}",
        value=round(EURBUSD_rate, 3),
        delta=round(EURBUSD_rate - USD_purchase_price, 3),
        delta_color="inverse",
    )

klines_df = pd.DataFrame(data=[date.today() - timedelta(days=x) for x in range(180)])
# for el in summary.index:
# klines_df[el] = get_hist_klines(el)["close"]
col1, col2 = st.columns(2)
with col1:
    st.dataframe(klines_df)
with col2:
    st.dataframe(get_hist_klines("BTCBUSD")[["close_time_dt", "close"]])
# st.metric(label="EUR", value=sum(summary.invested) / EURBUSD_rate, delta=sum(summary.cur_val) / EURBUSD_rate)
st.dataframe(summary[["average_buy_price", "pnl"]])
els = st.tabs(symbol_list)
for el in els:
    with el:
        st.write("Hello workd")
st.header("Overview 📈")

# symbol_filter_df = investment_stats_df["symbol"].isin(symbol_filter)
st.dataframe(investment_stats_df, use_container_width=True)
st.download_button(
    "download",
    data=investment_stats_df.to_csv(),
    file_name="latest.csv",
    mime="text/csv",
)

# def highlight_survived(s):
#     return ['background-color: green']*len(s) if s.symbol=='BTCBUSD' else ['background-color: red']*len(s)
# def color_survived(val):
#     color = 'dimgray' if val=='BTCBUSD' else 'transparent'
#     return f'background-color: {color}'
# st.dataframe(investment_stats_df.style.apply(highlight_survived, axis=1))
# st.dataframe(investment_stats_df.style.applymap(color_survived, subset=['Survived']))


st.title("Fear and Greed index")
# https://alternative.me/crypto/fear-and-greed-index/
# https://alternative.me/crypto/fear-and-greed-index/#api


def get_fng():
    r = requests.get("https://api.alternative.me/fng/?limit=45")
    data = r.json().get("data")
    return data


data = get_fng()
t45d_avg = round(np.mean([int(el["value"]) for el in data]))
current_classification = data[0]["value_classification"]
current_value = int(data[0]["value"])


def get_bar_color(val):
    if val < 25:
        return "rgba(155, 40, 40, .4)"
    elif 25 <= val < 50:
        return "rgba(253, 127, 57, .4)"
    elif 50 <= val < 75:
        return "rgba(253, 253, 95, .4)"
    else:
        return "rgba(30, 255, 102, .4)"


gauge_fig = go.Figure(
    go.Indicator(
        mode="gauge+number+delta",
        value=current_value,
        domain={"x": [0, 1], "y": [0, 1]},
        title={"text": current_classification, "font": {"size": 44}},
        delta={"reference": t45d_avg},
        gauge={
            "bar": {"color": get_bar_color(current_value)},
            "axis": {"range": [0, 100], "tickwidth": 1, "dtick": 25},
            "steps": [
                {"range": [0, 25], "color": "rgba(155, 40, 40, .4)"},
                {"range": [25, 50], "color": "rgba(253, 127, 57, .4)"},
                {"range": [50, 75], "color": "rgba(253, 253, 95, .4)"},
                {"range": [75, 100], "color": "rgba(30, 255, 102, .4)"},
            ],
        },
    )
)

historical_df = pd.DataFrame.from_records(data)
historical_df["date"] = historical_df["timestamp"].apply(lambda x: datetime.fromtimestamp(int(x)))
historical_df["value"] = historical_df["value"].astype(int)

historical_fig = go.Figure()
historical_fig.add_trace(go.Scatter(x=historical_df["date"], y=historical_df["value"], mode="lines", name="lines"))
# historical_fig.update_layout(showlegend=False, plot_bgcolor="white", margin=dict(t=10, l=10, b=10, r=10))

fig = px.line(
    historical_df,
    x="date",
    y="value",
    markers=True,
)
col1, col2 = st.columns(2)
with col1:
    st.plotly_chart(gauge_fig)
with col2:
    st.plotly_chart(fig)
