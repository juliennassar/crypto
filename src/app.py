import json
from datetime import date, datetime, timedelta
from io import StringIO

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
import streamlit as st

from data_api import (
    compute_investment_stats,
    get_avg_price_for_symbol,
    get_hist_klines,
    symbol_prices,
)
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
symbol_list.remove(EURBUSD_symbol)
current_prices = symbol_prices(symbol_list)


summary = (
    investment_stats_df[investment_stats_df["symbol"] != EURBUSD_symbol]
    .groupby("symbol")
    .agg({"average_buy_price": "last", "holding": "last", "realized_gains": "sum"})
    .join(current_prices)
)
summary["value"] = summary.price * summary.holding
summary["invested"] = summary.average_buy_price * summary.holding
summary["pnl"] = summary.value - summary.invested

with st.sidebar:
    # currency = st.radio(
    #     label="currency",
    #     options=["USD", "EUR"],
    #     horizontal=True
    # )
    delta_type = st.radio(
        label="delta",
        options=["pct", "abs"],
        horizontal=True,
        key="delta_type",
    )


def display_delta(current, benchmark, delta_type=st.session_state.delta_type):
    if delta_type == "pct":
        val = (current - benchmark) * 100.0 / benchmark
        return f"{val:.2f}%"
    else:
        val = current - benchmark
        if val > 100:
            return f"{round(val)} USD"
        elif val > 10:
            return f"{round(val, 1)} USD"
        else:
            return f"{round(val, 3)} USD"

euros_invested = sum(
    investment_stats_df[
        (investment_stats_df["symbol"] == EURBUSD_symbol)
        & (investment_stats_df["is_buyer"] == 0)
    ].quantity
) - sum(
    investment_stats_df[
        (investment_stats_df["symbol"] == EURBUSD_symbol)
        & (investment_stats_df["is_buyer"] == 1)
    ].quantity
)
usd_invested = round(
    sum(
        investment_stats_df[
            (investment_stats_df["symbol"] == EURBUSD_symbol)
            & (investment_stats_df["is_buyer"] == 0)
        ].quote_quantity
    )
    - sum(
        investment_stats_df[
            (investment_stats_df["symbol"] == EURBUSD_symbol)
            & (investment_stats_df["is_buyer"] == 1)
        ].quote_quantity
    ),
    0,
)

st.title("Crypto dashboard")

st.header(f"Invested {euros_invested:.2f} EUR")

col1, col2 = st.columns([3, 1])
with col1:
    total = pd.DataFrame()
    for symbol in symbol_list:
        df = get_hist_klines(symbol, limit=360)[["close_time_dt", "close"]]
        if total.empty:
            total["dt"] = df["close_time_dt"]
            total["value"] = 0.0
        total[symbol] = df.close * summary.loc[symbol].holding
        total["value"] += total[symbol]
    st.line_chart(total, x="dt", y=symbol_list + ["value"])
with col2:
    portfolio_value = sum(summary.holding * summary.price)
    st.metric(
        label="Portfolio",
        value=round(portfolio_value, 2),
        delta=display_delta(portfolio_value, usd_invested),
    )
    USD_purchase_price = usd_invested / euros_invested
    # st.metric(
    #     label=f"EUR/BUSD {USD_purchase_price:.3f}",
    #     value=round(EURBUSD_rate, 3),
    #     delta=display_delta(EURBUSD_rate, USD_purchase_price)
    #     delta_color="inverse",
    # )


for index, row in summary.sort_values(["invested"], ascending=False).iterrows():
    if row["invested"] == 0:
        continue
    title = f'{index} {display_delta(row["price"],row["average_buy_price"], "pct")}, \
    {display_delta(row["price"],row["average_buy_price"], "abs")}'
    with st.expander(title):
        col1, col2 = st.columns(2)
        with col1:
            st.metric(
                label="Price",
                value=round(row["price"], 2),
                delta=display_delta(
                    current=row["price"],
                    benchmark=row["average_buy_price"],
                ),
            )
        with col2:
            st.metric(
                label="P&L",
                value=round(row["value"], 2),
                delta=display_delta(
                    current=row["value"],
                    benchmark=row["invested"],
                ),
            )

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
historical_df["date"] = historical_df["timestamp"].apply(
    lambda x: datetime.fromtimestamp(int(x))
)
historical_df["value"] = historical_df["value"].astype(int)

col1, col2 = st.columns(2)
with col1:
    st.plotly_chart(gauge_fig, use_container_width=True)
with col2:
    st.line_chart(historical_df, x="date", y="value")
