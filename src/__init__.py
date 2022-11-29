# import requests

# r = requests.get(
#     "https://rpilocator.com/feed/?country=UK&cat=PI4",
#     headers={"content-type": "application/json"},
# )
# print(r.content)

if __name__ == "__main__":
    import requests

    r = requests.get(
        "https://api.binance.com/api/v3/avgPrice", params={"symbol": "BTCBUSD"}
    )
    print(r.status_code)
    print(r.json())
