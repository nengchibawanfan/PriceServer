# -*- coding: utf-8 -*-
# Author: zhangchao
# Date: 2019/3/15
# Desc: 订阅各个交易所的成交价格，获取coin兑换法币的价格
import time

import redis
import requests
from retry import retry
import multiprocessing.dummy

from wssExchange import bytetrade, huobipro
from priceserver.commen.logger import getLog
from priceserver.conf.settings import HUOBIPRO_API, COIN_BASE_URL, BYTETRADE_API, COIN_CURRENCY, CURRENCY_LIST

moneyLst = CURRENCY_LIST
logger = getLog()


class Quote(object):

    def __init__(self):
        # 从coinbase获取法币的价格
        self.coinbase_api = COIN_BASE_URL + "v2/assets/summary"
        self.r = redis.StrictRedis(decode_responses=True)
        self.pool = multiprocessing.dummy.Pool(8)
        self.bt = bytetrade()
        self.hb = huobipro()
        self.response_symbols, self.markets, self.marketNames, self.marketId_ccxtsymbol_mapping = self.getMarketIds()

    def get_commen_symbols(self):
        logger.info("获取共同交易对")
        url = HUOBIPRO_API + "v1/common/symbols"
        res = eval(requests.get(url).content.decode("utf-8"))
        huobi_symbols = set([i["base-currency"].upper() + "/" + i["quote-currency"].upper() for i in res["data"]])
        bytetrade_symbol = set(self.marketNames)
        commen_symbol = huobi_symbols & bytetrade_symbol

        return list(commen_symbol)

    def parse_response(self, response):
        """
        解析response
        :param response:
        :return:
        """
        response = eval(response)
        # self.quote[base] = {}
        value = {}
        for symbol in response["data"]:
            coin = symbol["base"]
            price = symbol["latest"]
            value[coin] = price
        return value

    @retry(10, 3)
    def sendRequest(self, base):
        """
        构建请求并发送
        :param base: CNY USD
        :return:
        """
        params = {
            # "include_prices": "false",
            "base": base,
            "resolution": "hour"
        }
        response = requests.get(url=self.coinbase_api, params=params).content.decode("utf-8")
        return response

    def updateQuote(self, base):
        # 所有的法币名称
        response = eval(self.sendRequest(base))
        for symbol in response["data"]:
            if symbol["base"] in [i for i in COIN_CURRENCY]:
                k = symbol["base"] + "/" + symbol["currency"]
                price = symbol["latest"]
                # 将value写入到redis中
                self.r.hset("coinbase_currency_price", k, price)

    def start(self):
        """
        维持quote字典最新
        :return:
        """
        logger.info("更新法币价格")
        for base in moneyLst:
            # 所有的法币名称
            self.pool.apply_async(self.updateQuote, (base,))

    def cal_market_id(self, symbol):
        symbolPair = symbol.split('/')
        return int(symbolPair[1]) * 2147483647 + int(symbolPair[0])

    def cal_ccxt_symbol(self, market_id):
        return self.marketId_ccxtsymbol_mapping[str(market_id)]

    def onTicker_bytetrade(self, symbol, data):
        """
        subscribe的回调函数   将data写入到redis中
        :return:
        """
        s = self.cal_market_id(symbol)
        ccxt_symbol = self.cal_ccxt_symbol(s)
        # 将收到的symbol计算成 ccxtsymbol
        self.r.publish("price_server_" + "bytetrade_" + ccxt_symbol, data["last"])
        self.r.hset("price_server_bytetrade", ccxt_symbol, data["last"])

    def onDeal_huobipro(self, symbol, data):
        # 将收到的symbol计算成 ccxtsymbol

        self.r.publish("price_server_" + "huobipro_" + str(symbol), data[0]["info"]["price"])
        self.r.hset("price_server_huobipro", symbol, data[0]["info"]["price"])

    def subscribeAllTicker(self):
        """
        订阅所有的交易对的websocket   ticker
        :return:
        """
        self.bt.start()
        self.bt.subscribeTicker(self.markets, self.onTicker_bytetrade)
        logger.info("订阅bytetrade各个交易对成交价格")
        # 订阅我们有的火币也有的交易对
        self.hb.start()
        for symbol in self.get_commen_symbols():
            self.hb.subscribeDeals(symbol, self.onDeal_huobipro)
        logger.info("订阅火币各个交易对成交价格")

    def getMarketIds(self):
        logger.info("正在获取Market，MarketName，marketId与ccxtSymbol映射等信息")
        url = BYTETRADE_API + "?cmd=markets"
        res = eval(requests.get(url).content.decode("utf-8"))

        markets = [str(i["stockId"]) + "/" + str(i["moneyId"]) for i in res["symbols"] if i["money"] != "BTT"]  # "3/2"
        marketNames = [i["name"] for i in res["symbols"] if i["money"] != "BTT"]  # "CMT/KCASH"
        res_symbols = res["symbols"]
        coinId_ccxtsymbol_mapping = {str(i["id"]): i["name"] for i in res["symbols"] if i["money"] != "BTT"}
        return res_symbols, markets, marketNames, coinId_ccxtsymbol_mapping


if __name__ == '__main__':
    # 用来维护兑换法币的redis hash
    q = Quote()

    q.subscribeAllTicker()  # 维护各个marketId的实时价格
    while True:
        q.start()  # 维护法币的价格
        time.sleep(60)