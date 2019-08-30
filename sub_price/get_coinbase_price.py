# -*- coding: utf-8 -*-
# Author: zhangchao
# Date: 2019-07-18
# Desc: 获取coin兑换法币的价格
import sys

sys.path.append("..")

import time

import requests
import schedule

# from retry import retry
from multiprocessing.dummy import Pool

from priceserver.common.logger import getLog
from priceserver.common.db_connection import ConnectRedis
from priceserver.conf.settings import configs

HUOBIPRO_API = configs["exchange"]["huobi"]["api_url"]
COIN_BASE_URL = configs["exchange"]["coinbase"]["api_url"]
BYTETRADE_API = configs["exchange"]["bytetrade"]["restful_url"]
COIN_CURRENCY = configs["COIN_CURRENCY"]
CURRENCY_LIST = configs["CURRENCY_LIST"]

moneyLst = CURRENCY_LIST  # 法币的种类
logger = getLog()


class Quote(object):

    def __init__(self):
        # 从coinbase获取法币的价格
        self.r = ConnectRedis()
        self.coinbase_api = COIN_BASE_URL + "v2/assets/summary"
        self.pool = Pool(20)


    # @retry(10, 3)
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
                print(k, price)
                self.r.hset("coinbase_currency_price1", k, price)

    def start(self):
        """
        维持quote字典最新
        :return:
        """
        self.r.set("Receive_the_data_coinbase1", time.time())
        logger.info("更新法币价格")
        for base in moneyLst:
            # 所有的法币名称
            self.pool.apply_async(self.updateQuote, (base,))


if __name__ == '__main__':
    # 开始的时候将原来的键删掉，构建新的  一旦加了新的交易对，重启程序


    r = ConnectRedis()

    obj = Quote()


    while True:
        obj.start()  # 维护法币的价格
        time.sleep(60 * 2)
