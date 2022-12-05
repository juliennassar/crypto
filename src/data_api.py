# get latest trades CSV data
import csv
import json
from datetime import date, datetime, timedelta
from io import StringIO
from os import environ

import numpy as np
import pandas as pd
import pytz
import requests
import streamlit as st

from db import get_trades


def get_hist_klines(symbol, limit=180, interval="1d"):
    r = requests.get(
        "https://api.binance.com/api/v3/klines",
        params={
            "symbol": symbol,
            "interval": interval,
            "limit": limit,
        },
    )
    if r.status_code != 200:
        return None

    klines_df = pd.DataFrame.from_records(
        data=r.json(),
        columns=[
            "open_time",
            "open",
            "high",
            "low",
            "close",
            "volume",
            "close_time",
            "quote_asset_volume",
            "number_of_trades",
            "taker_buy_base_asset_volume",
            "taker_buy_quote_asset_volume",
            "ignore",
        ],
    )
    klines_df[["open", "high", "low", "close"]] = klines_df[
        ["open", "high", "low", "close"]
    ].astype(float)
    klines_df[["open_time_dt", "close_time_dt"]] = klines_df[
        ["open_time", "close_time"]
    ].applymap(lambda x: datetime.fromtimestamp(x // 1000, tz=pytz.utc))
    return klines_df


def get_avg_price_for_symbol(symbol: str) -> float:
    r = requests.get(
        "https://api.binance.com/api/v3/avgPrice", params={"symbol": symbol}
    )
    if r.status_code != 200:
        return None
    price_data = r.json()
    return float(price_data.get("price"))


def get_avg_prices(df: pd.DataFrame) -> pd.DataFrame:
    data = []
    for symbol in df["symbol"].unique():
        price = get_avg_price_for_symbol(symbol)
        data.append((symbol, price))
    return pd.DataFrame(data=data, columns=["symbol", "price"])


def compute_investment(df) -> pd.DataFrame():
    """
    Compute the current invested amount fom EUR in BUSD
    """
    trades = df.sort_values("time", ascending=True)

    trades_eur = df[df["symbol"] == "EURBUSD"].sort_values("time", ascending=True)
    trades_eur["mult"] = 1
    trades_eur.loc[trades_eur["is_buyer"] == 1, "mult"] = -1

    trades_eur["eur"] = (trades_eur["quantity"] * trades_eur["mult"]).cumsum()
    trades_eur["busd"] = (
        trades_eur["quantity"] * trades_eur["price"] * trades_eur["mult"]
    ).cumsum()
    display = trades_eur[["date", "eur", "busd"]].groupby("date").last()
    # display["to_date"] = display["date"].shift(-1)
    # data = calendar_df.join(display)
    return display


def symbol_prices(symbol_list) -> pd.DataFrame:
    data = [(symbol, get_avg_price_for_symbol(symbol)) for symbol in symbol_list]
    return pd.DataFrame(data=data, columns=["symbol", "price"]).set_index("symbol")


def symbol_price_history(symbol_list) -> pd.DataFrame:
    data = [(symbol, get_hist_klines(symbol)) for symbol in symbol_list]
    return pd.DataFrame(data=data, columns=["symbol", "price"]).set_index("symbol")


def compute_investment_stats(df: pd.DataFrame) -> pd.DataFrame:
    # commission not taken into account
    df["average_buy_price"] = 0.0
    df["holding"] = 0.0
    df["realized_gains"] = 0.0

    for symbol in df["symbol"].unique():
        subset = df[df["symbol"] == symbol].sort_values("time")
        is_first = True
        for i in subset.index:
            quantity = df.iloc[i]["quantity"]
            price = df.iloc[i]["price"]
            quote_quantity = df.iloc[i]["quote_quantity"]

            if is_first:
                df.at[i, "average_buy_price"] = price
                df.at[i, "holding"] += quantity
                is_first = False
                continue

            cur_avg_buy_price = df.iloc[i - 1]["average_buy_price"]
            holding = df.iloc[i - 1]["holding"]

            if df.iloc[i]["is_buyer"] == 1:
                df.at[i, "average_buy_price"] = (
                    (cur_avg_buy_price * holding) + (quantity * price)
                ) / (holding + quantity)
                df.at[i, "holding"] = holding + quantity

            else:
                df.at[i, "average_buy_price"] = cur_avg_buy_price
                df.at[i, "holding"] = holding - quantity
                df.at[i, "realized_gains"] = quantity * (price - cur_avg_buy_price)

    return df
