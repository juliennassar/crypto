import hashlib
import hmac
import time
from os import environ
from urllib.parse import urlencode

import pandas as pd
import requests
import streamlit as st

st.set_page_config(
    page_title="binance",
    page_icon="./bitcoin.png",
    layout="wide",
)

BINANCE_API_KEY = environ.get("BINANCE_API_KEY")
BINANCE_API_SECRET = environ.get("BINANCE_API_SECRET")


def binance_get_open_orders(symbol=None):
    data = {
        "timestamp": int(time.time() * 1000),
    }
    if symbol:
        data["symbol"] = symbol
    m = hmac.new(
        key=BINANCE_API_SECRET.encode("utf-8"),
        msg=urlencode(data).encode("utf-8"),
        digestmod=hashlib.sha256,
    )
    data["signature"] = m.hexdigest()
    r = requests.get(
        "https://api.binance.com/api/v3/openOrders",
        params=data,
        headers={"X-MBX-APIKEY": BINANCE_API_KEY},
    )
    if r.status_code != 200:
        return None
    return r.json()


open_orders = binance_get_open_orders()
st.dataframe(pd.DataFrame.from_dict(open_orders))
