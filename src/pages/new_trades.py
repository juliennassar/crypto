import hashlib
import hmac
import shutil
import time
from os import environ
from urllib.parse import urlencode

import pandas as pd
import requests
import streamlit as st

from data_api import get_trades_df

st.set_page_config(
    page_title="new trades",
    page_icon="./bitcoin.png",
    layout="wide",
)

BINANCE_API_KEY = environ.get("BINANCE_API_KEY")
BINANCE_API_SECRET = environ.get("BINANCE_API_SECRET")


def binance_get_my_trades(symbol, binance_trade_id):
    data = {
        "symbol": symbol,
        "fromId": binance_trade_id,
        "timestamp": int(time.time() * 1000),
    }
    m = hmac.new(
        key=BINANCE_API_SECRET.encode("utf-8"),
        msg=urlencode(data).encode("utf-8"),
        digestmod=hashlib.sha256,
    )
    data["signature"] = m.hexdigest()
    r = requests.get(
        "https://api.binance.com/api/v3/myTrades",
        params=data,
        headers={"X-MBX-APIKEY": BINANCE_API_KEY},
    )
    if r.status_code != 200:
        return None
    return r.json()


def get_new_trades_df(symbol, binance_trade_id):
    binance_data = binance_get_my_trades(
        symbol=symbol,
        binance_trade_id=binance_trade_id,
    )
    if not binance_data:
        return pd.DataFrame()

    binance_data_df = pd.DataFrame.from_records(binance_data)
    binance_data_df["binance_id"] = binance_data_df["id"]
    return binance_data_df[
        [
            "symbol",
            "binance_id",
            "price",
            "qty",
            "quoteQty",
            "commission",
            "commissionAsset",
            "time",
            "isBuyer",
        ]
    ]


def insert_new_trades(*args, **kwargs):
    trades_df = get_trades_df()
    new_trades_df = kwargs.get("new_trades_df")
    all_trades_df = pd.concat([trades_df, new_trades_df])

    shutil.copy(src="/trades/latest.csv", dst=f"/trades/{int(time.time())}.csv")
    with open(file="/trades/latest.csv", mode="w") as latest_file:
        latest_file.write(all_trades_df.sort_values(["symbol", "time"]).to_csv())


trades_df = get_trades_df()
latest_trade_id_per_symbol = trades_df.groupby("symbol").agg({"binance_id": "max"})

new_trades_df = pd.DataFrame()
i = 0.0
prog = 1.0 / len(latest_trade_id_per_symbol)
progress = st.progress(i)
for symbol, binance_trade_id in latest_trade_id_per_symbol.itertuples():
    binance_data_df = get_new_trades_df(
        symbol=symbol,
        binance_trade_id=binance_trade_id + 1,
    )
    new_trades_df = pd.concat([new_trades_df, binance_data_df], ignore_index=True)
    i += prog
    progress.progress(i)

progress.progress(1.0)

if new_trades_df.empty:
    st.info("no new trades detected")
else:
    st.dataframe(new_trades_df)
    st.button(
        "insert",
        on_click=insert_new_trades,
        args=(new_trades_df,),
        kwargs={"new_trades_df": new_trades_df},
    )
