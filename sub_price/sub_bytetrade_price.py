# -*- coding: utf-8 -*-
# Author: zhangchao
# Date: 2019-07-18
# Desc:
import re
import sys

import numpy
from tslearn.generators import random_walks
from tslearn.preprocessing import TimeSeriesScalerMinMax
from scipy import interpolate
import threading

sys.path.append("..")
import time

import requests
import multiprocessing.dummy

from wssExchange import bytetrade
from priceserver.common.logger import getLog
from priceserver.common.db_connection import ConnectRedis
from priceserver.conf.settings import configs
TARGETEXCHANGE = configs["target_exchange"]
PAIRS = configs["pairs"]
BYTETRADE_API = configs["exchange"]["bytetrade"]["restful_url"]

log = getLog()

Activity = [59, 20, 10, 4, 2]


class Quote(object):

    def __init__(self):
        # 从coinbase获取法币的价格
        self.r = ConnectRedis()
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

        self.dataReady = False
        self.refExchanges = []
        self.tarExchange = TARGETEXCHANGE
        for v in PAIRS.values():
            if v['mode'] == 'refDirect':
                if v['exchange'] not in self.refExchanges:
                    self.refExchanges.append(v['exchange'])
            if v['mode'] == 'refDouble':
                if v['basePair']['exchange'] not in self.refExchanges:
                    self.refExchanges.append(v['basePair']['exchange'])
                if v['quotePair']['exchange'] not in self.refExchanges:
                    self.refExchanges.append(v['quotePair']['exchange'])
        super(Quote, self).__init__()
        # 自动生成的价格
        self.generatedPrice = {}
        # 币对参考价
        self.refPrice = {}
        # 币对最后价格
        self.lastPrice = {}
        # 最后成交数据
        self.lastDeal = {}
        # 最后ticker数据
        self.lastTicker = {}
        # 最后深度数据
        self.lastDepth = {}
        self.marketData = {}
        self.tickerSymbols = {}
        self.tickLock = threading.Lock()
        self.dealLock = threading.Lock()
        self.depthLock = threading.Lock()

    def start_price_manager(self):
        timerThread = threading.Thread(target=self.runTimer)
        timerThread.start()

    def runTimer(self):
        lastCheckRef = {}
        while True:
            try:
                for pair in PAIRS:
                    interval = Activity[int(PAIRS[pair]['activity']) - 1]
                    if not lastCheckRef.get(pair) or time.time() - lastCheckRef[pair] >= interval:
                        lastCheckRef[pair] = time.time()
                        if PAIRS[pair]['mode'] == 'refSelf' and self.generatedPrice.get(pair):
                            self.refPrice[pair] = self.generatedPrice[pair].pop(0)
                            self.r.hset("next_price", pair, self.generatedPrice[pair].pop(0))
                            log.info('on time pop ref self price %s, left %s' % (
                                self.refPrice[pair], len(self.generatedPrice[pair])))
            except Exception as e:
                log.error(e)
            time.sleep(1)

    # 检查自报价
    def __checkSelfRefPrice(self, symbol, lastPrice):
        iniPrice = PAIRS[symbol]['iniPrice']
        if not lastPrice:
            lastPrice = iniPrice
        priceRange = PAIRS[symbol]['priceRange']
        redisSeed = self.r.get(f'seedPrice.{symbol}')
        print(f"最后成交价格: {lastPrice}")
        print(f"初始价格：{iniPrice}")
        print(f"价格区间：{priceRange}")
        print(f"redis价格：{redisSeed}")
        print(f"参考价格：{self.refPrice}")
        print(f"generatedPrice: {self.generatedPrice}")
        seeds = {}
        if redisSeed: seeds = eval(redisSeed)
        if (self.refPrice.get(symbol) and lastPrice != iniPrice and
                abs(lastPrice - self.refPrice[symbol]) / lastPrice > priceRange * 0.2
                and abs(lastPrice - self.refPrice[symbol]) / lastPrice > 0.03 and self.generatedPrice.get(symbol)):
            log.info('current price %s is so far from ref price %s, regenerate ref price to fit it.'
                     % (lastPrice, self.refPrice[symbol]))
            self.generatedPrice[symbol] = None
            seeds[symbol] = None
        # 重新生成seedPrice，并存储
        if not seeds.get(symbol):
            seeds[symbol] = lastPrice
            log.info('regenerate seedPrice: %s' % seeds[symbol])
            self.r.set(f'seedPrice.{symbol}', f'{seeds}')
        # generatePrice为空，生成
        if not self.generatedPrice.get(symbol):
            self.generatedPrice[symbol] = self.__generateRefPrice(lastPrice, seeds[symbol], priceRange)
            log.info('generate ref price by seed %s, lastPrice %s, priceRange %s, data %s'
                     % (seeds[symbol], lastPrice, priceRange, len(self.generatedPrice[symbol])))
            self.refPrice[symbol] = self.generatedPrice[symbol].pop(0)
        # random_pop = numpy.random.uniform(0,1)
        # random_fluc = numpy.random.uniform(-0.0005,0.0005) #config.settings['pairs'][symbol]['priceRange']*numpy.random.uniform(-0.1,0.1)
        # if random_pop>numpy.random.uniform(0.5, 0.9) or not self.refPrice.get(symbol):
        #     self.refPrice[symbol] = self.generatedPrice[symbol].pop(0)
        #     log.info('pop last ref price %s'%self.refPrice[symbol])
        # else:
        #     # self.refPrice[symbol] = self.refPrice[symbol]*(1+random_fluc)
        #     log.info('random last ref price %s'%self.refPrice[symbol])

    def __generateRefPrice(self, curPrice, seedPrice, priceRange):
        priceMin = min(curPrice, seedPrice / 1.05 * (1 + numpy.random.uniform(-priceRange * 0.1, priceRange * 0.4)))
        priceMax = max(curPrice, seedPrice * 1.05 * (1 + numpy.random.uniform(-priceRange * 0.4, priceRange * 0.1)))
        data_len = numpy.random.randint(10000, 30000)

        # assert curPrice>=priceMin and curPrice<=priceMax,f"error: {curPrice}, {priceMin}, {priceMax}"
        def smooth_data(data):
            x = numpy.arange(0, len(data), 1)
            x_new = numpy.arange(0, max(x), 0.01)
            func = interpolate.interp1d(x, data, kind='quadratic')
            smoothed = func(x_new)
            return smoothed

        while True:
            dataset = random_walks(n_ts=1, sz=data_len * 2)
            scaler = TimeSeriesScalerMinMax(min=float(priceMin), max=float(priceMax))
            dataset_scaled = scaler.fit_transform(dataset)[0, :, 0]
            for i in range(0, data_len):
                if abs(dataset_scaled[i] - curPrice) / curPrice < 0.001:
                    # return list(smooth_data(dataset_scaled[i:i+data_len]))
                    with open('price.txt', 'w+') as f:
                        f.writelines([f'{p}\n' for p in dataset_scaled[i:i + data_len]])
                    return list(dataset_scaled[i:i + data_len])

    def cal_market_id(self, symbol):
        symbolPair = symbol.split('/')
        return int(symbolPair[1]) * 2147483647 + int(symbolPair[0])

    def cal_ccxt_symbol(self, market_id):
        return self.marketId_ccxtsymbol_mapping[str(market_id)]

    def onDeal_bytetrade(self, symbol, data):
        """
        subscribe的回调函数   将data写入到redis中
        :return:
        """
        # with self.dealLock:
        #     self.saveDeals(exchange, symbol, data)
        #     for deal in data:
        # self.lastPrice[exchange][symbol]=float(deal['price'])
        # exchange = "bytetrade"
        print(f"symbol: {symbol}    onDeal{data}")


        if symbol in PAIRS.keys():
            print(symbol)
            print("=" * 100)
            # self.saveDeals(exchange, symbol, dealData)

            self.__checkSelfRefPrice(symbol, float(data[0]["info"]["price"]))

        self.r.set("Receive_the_data_bytetrade1", time.time())
        s = self.cal_market_id(symbol)
        ccxt_symbol = self.cal_ccxt_symbol(s)
        # 将收到的symbol计算成 ccxtsymbol
        # self.r.publish("price_server_" + "bytetrade_" + ccxt_symbol, data["last"])
        self.r.hset("price_server_bytetrade1", ccxt_symbol, float(data[0]["info"]["price"]))
        self.r.set("Receive_the_data_bytetrade1", time.time())

    def onTicker_bytetrade(self, symbol, data):
        """
        subscribe的回调函数   将data写入到redis中
        :return:
        """
        print(f"symbol: {symbol}    onTicker{data}")

        s = self.cal_market_id(symbol)
        ccxt_symbol = self.cal_ccxt_symbol(s)
        # 将收到的symbol计算成 ccxtsymbol


        if symbol in ["48/2"]:
            pass
        else:

            # self.r.publish("price_server_" + "bytetrade_" + ccxt_symbol, data["last"])
            self.r.hset("price_server_bytetrade_today1", ccxt_symbol, str(data["info"]))
            self.r.set("Receive_the_data_bytetrade1", time.time())

    def subscribeAllDeal(self):
        """
        订阅所有的交易对的websocket   ticker
        :return:
        """
        self.bt.start()
        self.bt.subscribeDeals(self.markets, self.onDeal_bytetrade)
        log.info("订阅bytetrade各个交易对最近成交")

    def subscribeAllTicker(self):
        self.bt.start()
        self.bt.subscribeTicker(self.markets, self.onTicker_bytetrade)
        log.info("订阅bytetrade各个交易对today")

    def getMarketInfos(self):
        # 获取交易所正在进行的市场
        log.info("正在获取目前交易所支持的 Market，MarketName，marketId与ccxtSymbol映射等信息")
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
    #
    # def push_bear():
    #     PUSH_BEAR_KEY = "11970-ba5f3d1644a4bd880a04ebdef3560f69"
    #     import requests
    #     url = "https://pushbear.ftqq.com/sub"
    #     data = {
    #         "sendkey": PUSH_BEAR_KEY,
    #         "text": "PriceServer——GraphQL",
    #         "desp": "bytetrade数据获取重启"
    #     }
    #     headers = {
    #         "Accept": "application/json, text/javascript, */*; q=0.01",
    #         "Accept-Encoding": "gzip, deflate, br",
    #         "User-Agent": "Mozilla/5.0 (Windows NT 6.1; WOW64; rv:47.0) Gecko/20100101 Firefox/47.0"}
    #     requests.post(url, data=data, headers=headers)
    #
    #
    # # push_bear()
    # r = ConnectRedis()
    # # r.delete("price_server_bytetrade_today")
    # r.delete("price_server_bytetrade1")
    #
    # # HLB/USD       写死
    # r.hset("price_server_bytetrade1", "HLB/USD", "0.0001486")
    # log.info("将 HLB/USD 价格写死为0.0001486")

    # 用来维护兑换法币的redis hash
    q = Quote()
    q.start_price_manager()
    # q.get_price_by_rest()
    #
    q.subscribeAllDeal()  # 维护各个marketId的实时价格
    q.subscribeAllTicker()  # 维护各个marketId的实时价格
