# -*- coding: utf-8 -*-
# Author: zhangchao
# Date: 2019-07-18
# Desc:

import sys

sys.path.append("..")
import time
import ccxt

import requests

from wssExchange import huobipro
from priceserver.common.logger import getLog
from priceserver.common.db_connection import ConnectRedis
from priceserver.conf.settings import configs
from priceserver.common.tools import get_market_name_num_mapping

BYTETRADE_API = configs["exchange"]["bytetrade"]["restful_url"]
HUOBIPRO_API = configs["exchange"]["huobi"]["api_url"]
logger = getLog()
MARKET_NAME_NUM_MAPPING = get_market_name_num_mapping()
PAIRS = configs["pairs"]


class Quote(object):

    def __init__(self):
        self.r = ConnectRedis()
        self.hb = huobipro()
        # 获取交易界面上的交易对，
        # 接口返回信息
        self.response_symbols = None
        # 交易所目前的市场  3/2
        self.markets = None
        # 交易所支持的市场名称   ETH/BTC
        self.marketNames = None
        # 市场id与市场name映射s
        self.marketId_ccxtsymbol_mapping = None
        self.getMarketInfos()
        print(self.marketNames)

    def get_huobipro_symbols(self):
        logger.info("获取火币交易对")
        url = HUOBIPRO_API + "v1/common/symbols"
        res = eval(requests.get(url).content.decode("utf-8"))
        huobi_symbols = [i["base-currency"].upper() + "/" + i["quote-currency"].upper() for i in res["data"]]

        return huobi_symbols

    def onDeal_huobipro(self, symbol, data):
        print(symbol)
        print(data)
        # 将收到的symbol计算成 ccxtsymbol
        self.r.set("Receive_the_data_huobi1", time.time())
        if MARKET_NAME_NUM_MAPPING[symbol] in PAIRS.keys() and PAIRS[MARKET_NAME_NUM_MAPPING[symbol]][
            "mode"] == "refSelf":
            pass
        else:
            self.r.hset("next_price", MARKET_NAME_NUM_MAPPING[symbol], data[0]["info"]["price"])

        # self.r.publish("price_server_" + "huobipro_" + str(symbol), data[0]["info"]["price"])
        self.r.hset("price_server_huobipro1", symbol, data[0]["info"]["price"])

    def subscribeAllTicker(self):
        """
        订阅所有的交易对的websocket   ticker
        :return:
        """
        # 订阅我们有的火币所有的交易对
        self.hb.start()
        huobipro_symbols = set(self.get_huobipro_symbols())
        # 我们有并且火币也有的交易对
        bytetrade_symbols = set([i for i in self.marketNames if "BTT" not in i])

        common_symbols = huobipro_symbols & bytetrade_symbols

        common_symbols.update(["ETH/USDT", "BTC/USDT"])

        for stock in common_symbols:
            self.hb.subscribeDeals(stock, self.onDeal_huobipro)
        logger.info("订阅火币各个交易对成交价格")

    def getMarketInfos(self):
        # 获取交易所正在进行的市场
        logger.info("正在获取目前交易所支持的 Market，MarketName，marketId与ccxtSymbol映射等信息")
        url = BYTETRADE_API + "?cmd=marketsPrice&channel=all"
        res = eval(requests.get(url).content.decode("utf-8"))

        markets = [str(i["stockId"]) + "/" + str(i["moneyId"]) for i in res["result"]]  # "3/2"
        marketNames = [i["name"] for i in res["result"]]  # "CMT/KCASH"
        res_symbols = res["result"]
        coinId_ccxtsymbol_mapping = {str(i["id"]): i["name"] for i in res["result"]}
        # 接口返回信息
        self.response_symbols = res_symbols
        # 交易所目前的市场  3/2
        self.markets = markets
        # 交易所支持的市场名称
        self.marketNames = marketNames
        # 市场id与市场name映射
        self.marketId_ccxtsymbol_mapping = coinId_ccxtsymbol_mapping

    def get_price_by_rest(self):

        huobipro_symbols = set(self.get_huobipro_symbols())
        # 我们有并且火币也有的交易对
        bytetrade_symbols = set([i for i in self.marketNames if "BTT" not in i])

        common_symbols = huobipro_symbols & bytetrade_symbols

        huobipro = ccxt.huobipro()
        res = huobipro.fetch_tickers()
        for h_symbol, v in res.items():
            if h_symbol in common_symbols or h_symbol in ["ETH/USDT", "BTC/USDT"]:
                self.r.hset("price_server_huobipro1", h_symbol, v["close"])
        self.r.set("Receive_the_data_huobi1", time.time())


if __name__ == '__main__':
    # 开始的时候将原来的键删掉，构建新的  一旦加了新的交易对，重启程序

    def push_bear():
        PUSH_BEAR_KEY = "11970-ba5f3d1644a4bd880a04ebdef3560f69"
        import requests
        url = "https://pushbear.ftqq.com/sub"
        data = {
            "sendkey": PUSH_BEAR_KEY,
            "text": "PriceServer——GraphQL",
            "desp": "huobipro数据获取重启"
        }
        headers = {
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "Accept-Encoding": "gzip, deflate, br",
            "User-Agent": "Mozilla/5.0 (Windows NT 6.1; WOW64; rv:47.0) Gecko/20100101 Firefox/47.0"}
        requests.post(url, data=data, headers=headers)


    # push_bear()
    r = ConnectRedis()
    # r.delete("price_server_huobipro")

    # 用来维护兑换法币的redis hash
    q = Quote()
    q.get_price_by_rest()
    #
    q.subscribeAllTicker()  # 维护各个marketId的实时价格
