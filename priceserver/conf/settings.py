from priceserver.common.db_connection import ConnectRedis

HUOBIPRO_API = "https://api.huobi.pro/"
BYTETRADE_API = "https://api.bytetrade.io/bittrade/v1/me"
BYTETRADE_TEST_API = "https://c2.bytetrade.io/bittrade/v1/me"
COIN_BASE_URL = "https://api.coinbase.com/"
PUSH_BEAR_KEY = "11970-ba5f3d1644a4bd880a04ebdef3560f69"


def get_symbol_list():
    import requests
    url = BYTETRADE_API + "?cmd=marketsPrice"
    res = eval(requests.get(url).content.decode("utf-8"))
    # marketNames = [i["name"] for i in res["symbols"] if i["money"] and i["stock"] != "BTT"]  # "CMT/KCASH"
    marketNames = [i["name"] for i in res["result"]]  # "CMT/KCASH"
    symbolNames = []  # "CMT/KCASH"
    for market in marketNames:
        stock, money = market.split("/")
        symbolNames.append(stock)
        symbolNames.append(money)


    # url = HUOBIPRO_API + "v1/common/symbols"
    # res = eval(requests.get(url).content.decode("utf-8"))
    # huobi_symbols = set([i["base-currency"].upper() + "/" + i["quote-currency"].upper() for i in res["data"]])
    bytetrade_markets = set(marketNames)
    bytetrade_symbols = set(symbolNames)
    # commen_symbol = huobi_symbols & bytetrade_symbol

    return list(bytetrade_markets), list(bytetrade_symbols)


# redis
REDIS_HOST = '127.0.0.1'
REDIS_PORT = 6379

MARKET_LIST, SYMBOL_LIST = get_symbol_list()
# 默认的交易对的列表，就是 我们交易所支持的所有的币对

EXCHANGE_LIST = ["huobipro", "bytetrade"]
# 支持的交易所

CURRENCY_LIST = ["CNY", "USD", "GBP", "SGD", "HKD", "JPY", "CAD", "AUD", "EUR", "THB", "NZD", "KRW", "RUB", "MYR"]
# 人民币     美元 英镑  新加坡元  港币  日元    还拿大元  澳大利亚元   欧元  泰铢   新西兰元  韩元  俄罗罗罗罗斯  马来西亚林吉特

COIN_CURRENCY = ["BTC", "ETH"]
# 保存的兑法币价格的币种   在订阅中的设置

PRIORITY = ["ETH", "BTC"]
# 优先级


if __name__ == '__main__':
    print(SYMBOL_LIST)
