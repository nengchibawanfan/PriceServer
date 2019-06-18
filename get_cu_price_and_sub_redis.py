# -*- coding: utf-8 -*-
# Author: zhangchao
# Date: 2019/3/15
# Desc: 订阅各个交易所的成交价格，获取coin兑换法币的价格
import time
import ccxt

import redis
import requests
from retry import retry
import multiprocessing.dummy

from wssExchange import bytetrade, huobipro
from priceserver.common.logger import getLog
from priceserver.common.db_connection import ConnectRedis
from priceserver.conf.settings import HUOBIPRO_API, COIN_BASE_URL, BYTETRADE_API, COIN_CURRENCY, CURRENCY_LIST

moneyLst = CURRENCY_LIST  # 法币的种类
logger = getLog()


class Quote(object):

    def __init__(self):
        # 从coinbase获取法币的价格
        self.coinbase_api = COIN_BASE_URL + "v2/assets/summary"
        self.r = redis.StrictRedis(decode_responses=True)
        self.pool = multiprocessing.dummy.Pool(8)
        self.bt = bytetrade()
        self.hb = huobipro()
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

    def get_huobipro_symbols(self):
        logger.info("获取火币交易对")
        url = HUOBIPRO_API + "v1/common/symbols"
        res = eval(requests.get(url).content.decode("utf-8"))
        huobi_symbols = [i["base-currency"].upper() + "/" + i["quote-currency"].upper() for i in res["data"]]

        return huobi_symbols

    def parse_response(self, response):
        """
        解析response
        :param response:
        :return:
        """
        response = eval(response)
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
            if symbol["base"] in COIN_CURRENCY:
                k = symbol["base"] + "/" + symbol["currency"]
                price = symbol["latest"]
                # 将value写入到redis中
                self.r.set("Receive_the_data_coinbase", time.time())
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
        self.r.set("Receive_the_data_bytetrade", time.time())
        s = self.cal_market_id(symbol)
        ccxt_symbol = self.cal_ccxt_symbol(s)
        # 将收到的symbol计算成 ccxtsymbol
        self.r.publish("price_server_" + "bytetrade_" + ccxt_symbol, data["last"])
        self.r.hset("price_server_bytetrade", ccxt_symbol, data["last"])
        self.r.hset("price_server_bytetrade_today", ccxt_symbol, str(data["info"]))

    def onDeal_huobipro(self, symbol, data):
        # 将收到的symbol计算成 ccxtsymbol
        self.r.set("Receive_the_data_huobi", time.time())

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

        # 订阅我们有的火币所有的交易对
        self.hb.start()
        huobipro_symbols = self.get_huobipro_symbols()
        # 我们有并且火币也有的交易对

        huobi_sub_symbols = []
        for i in self.marketNames:
            for j in i.split("/"):
                if j in huobi_sub_symbols:
                    pass
                else:
                    huobi_sub_symbols.append(j)
        # 订阅火币所有的交易对
        huobipro = ccxt.huobipro()
        res = huobipro.fetch_tickers()

        for stock in huobi_sub_symbols:
            for h_symbol, v in res.items():
                if h_symbol in [stock + "/ETH", stock + "/BTC"]:
                    ccxt_symbol = h_symbol
                    self.hb.subscribeDeals(ccxt_symbol, self.onDeal_huobipro)
        logger.info("订阅火币各个交易对成交价格")

    def getMarketInfos(self):
        # 获取交易所正在进行的市场
        logger.info("正在获取目前交易所支持的 Market，MarketName，marketId与ccxtSymbol映射等信息")
        url = BYTETRADE_API + "?cmd=marketsPrice&channel=all"
        res = eval(requests.get(url).content.decode("utf-8"))

        markets = [str(i["stockId"]) + "/" + str(i["moneyId"]) for i in res["result"]]  # "3/2"
        marketNames = [i["name"] for i in res["result"]]    # "CMT/KCASH"
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
        # restful查一下最新的成交价格
        for info in self.response_symbols:
            ccxt_symbol = info["name"]
            if info["stockId"] or info["moneyId"] == 35:
                pass
            else:
                # self.r.publish("price_server_" + "bytetrade_" + ccxt_symbol, info["today"]["last"])
                self.r.hset("price_server_bytetrade", ccxt_symbol, info["today"]["last"])

        stock_symbol = []
        for i in self.marketNames:
            for j in i.split("/"):
                if j in stock_symbol:
                    pass
                else:
                    stock_symbol.append(j)

        huobipro = ccxt.huobipro()
        res = huobipro.fetch_tickers()
        for stock in stock_symbol:
            for h_symbol, v in res.items():
                if h_symbol in [stock + "/ETH", stock + "/BTC"]:
                    ccxt_symbol = h_symbol
                    self.r.publish("price_server_" + "huobipro_" + ccxt_symbol, v["close"])
                    self.r.hset("price_server_huobipro", ccxt_symbol, v["close"])

if __name__ == '__main__':
    # 开始的时候将原来的键删掉，构建新的  一旦加了新的交易对，重启程序

    def push_bear():
        PUSH_BEAR_KEY = "11970-ba5f3d1644a4bd880a04ebdef3560f69"
        import requests
        url = "https://pushbear.ftqq.com/sub"
        data = {
            "sendkey": PUSH_BEAR_KEY,
            "text": "PriceServer——GraphQL",
            "desp": "数据获取重启"
        }
        headers = {
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "Accept-Encoding": "gzip, deflate, br",
            "User-Agent": "Mozilla/5.0 (Windows NT 6.1; WOW64; rv:47.0) Gecko/20100101 Firefox/47.0"}
        requests.post(url, data=data, headers=headers)

    push_bear()
    r = ConnectRedis()
    r.delete("price_server_bytetrade")
    r.delete("price_server_huobipro")
    r.delete("price_server_bytetrade_today")
    r.delete("price_server_path")
    logger.info("删除bytetrade，huobipro的价格缓存，删除路径缓存")

    # HLB/USD       写死
    r.hset("price_server_bytetrade", "HLB/USD", "0.0001486")
    logger.info("将 HLB/USD 价格写死为0.0001486")

    # 用来维护兑换法币的redis hash
    q = Quote()
    q.get_price_by_rest()
    #
    q.subscribeAllTicker()  # 维护各个marketId的实时价格
    while True:
        q.start()  # 维护法币的价格
        time.sleep(60 * 2)
