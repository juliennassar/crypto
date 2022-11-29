import sqlite3

import pandas as pd

DATABASE_PATH = "/db/trades.sqlite"


def get_trades() -> pd.DataFrame:
    con = sqlite3.connect(DATABASE_PATH)
    data = pd.read_sql_query("select * from trades", con)
    con.close()
    return data
