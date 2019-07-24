# -*- coding: utf-8 -*-
# Author: zhangchao
# Date: 2019-07-18
# Desc:

import sys

sys.path.append("..")
import time

import redis
import requests
import multiprocessing.dummy

from wssExchange import bytetrade
from priceserver.common.logger import getLog
from priceserver.common.db_connection import ConnectRedis
from priceserver.conf.settings import BYTETRADE_API

logger = getLog()


class Quote(object):

    def __init__(self):
        # 从coinbase获取法币的价格
        self.r = redis.StrictRedis(decode_responses=True)
        self.pool = multiprocessing.dummy.Pool(8)
        self.bt = bytetrade()
        # 获取交易界面上的交易对，
        # 接口返回信息
        self.response_symbols = None
        # 交易所目前的市场  3/2
        self.markets = None
        # 交易所支持的市场名称   ETH/BTC
        self.marketNames = None
        # 市场id与市场name映射
        self.marketId_ccxtsymbol_mapping = None
        self.getMarketInfos()

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
        self.r.set("Receive_the_data_bytetrade1", time.time())
        s = self.cal_market_id(symbol)
        ccxt_symbol = self.cal_ccxt_symbol(s)
        print(data)
        # 将收到的symbol计算成 ccxtsymbol
        # self.r.publish("price_server_" + "bytetrade_" + ccxt_symbol, data["last"])
        self.r.hset("price_server_bytetrade1", ccxt_symbol, data["last"])
        self.r.hset("price_server_bytetrade_today1", ccxt_symbol, str(data["info"]))
        self.r.set("Receive_the_data_bytetrade1", time.time())



    def subscribeAllTicker(self):
        """
        订阅所有的交易对的websocket   ticker
        :return:
        """
        self.bt.start()
        self.bt.subscribeTicker(self.markets, self.onTicker_bytetrade)
        logger.info("订阅bytetrade各个交易对成交价格")

    def getMarketInfos(self):
        # 获取交易所正在进行的市场
        logger.info("正在获取目前交易所支持的 Market，MarketName，marketId与ccxtSymbol映射等信息")
        url = BYTETRADE_API + "?cmd=marketsPrice&channel=all"
        res = eval(requests.get(url).content.decode("utf-8"))

        markets = [str(i["stockId"]) + "/" + str(i["moneyId"]) for i in res["result"] if i["moneyId"] != 1]  # "3/2"
        marketNames = [i["name"] for i in res["result"] if i["moneyId"] != 1]  # "CMT/KCASH"
        res_symbols = res["result"]
        coinId_ccxtsymbol_mapping = {str(i["id"]): i["name"] for i in res["result"]}
        # 接口返回信息
        self.response_symbols = res_symbols
        # 交易所目前的市场  3/2  除了／1   btt
        self.markets = markets
        # 交易所支持的市场名称
        self.marketNames = marketNames
        # 市场id与市场name映射
        self.marketId_ccxtsymbol_mapping = coinId_ccxtsymbol_mapping

    def get_price_by_rest(self):
        # restful查一下最新的成交价格
        for info in self.response_symbols:
            ccxt_symbol = info["name"]
            if info["stockId"] == 35:
                pass
            if info["moneyId"] == 1:

                print("=")
            else:
                print(ccxt_symbol)
                print(info)
                try:
                    self.r.hset("price_server_bytetrade1", ccxt_symbol, info["today"]["last"])
                except:
                    pass


if __name__ == '__main__':
    # 开始的时候将原来的键删掉，构建新的  一旦加了新的交易对，重启程序

    def push_bear():
        PUSH_BEAR_KEY = "11970-ba5f3d1644a4bd880a04ebdef3560f69"
        import requests
        url = "https://pushbear.ftqq.com/sub"
        data = {
            "sendkey": PUSH_BEAR_KEY,
            "text": "PriceServer——GraphQL",
            "desp": "bytetrade数据获取重启"
        }
        headers = {
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "Accept-Encoding": "gzip, deflate, br",
            "User-Agent": "Mozilla/5.0 (Windows NT 6.1; WOW64; rv:47.0) Gecko/20100101 Firefox/47.0"}
        requests.post(url, data=data, headers=headers)


    # push_bear()
    r = ConnectRedis()
    # r.delete("price_server_bytetrade_today")
    r.delete("price_server_bytetrade1")


    # HLB/USD       写死
    r.hset("price_server_bytetrade1", "HLB/USD", "0.0001486")
    logger.info("将 HLB/USD 价格写死为0.0001486")

    # 用来维护兑换法币的redis hash
    q = Quote()
    q.get_price_by_rest()
    #
    q.subscribeAllTicker()  # 维护各个marketId的实时价格
