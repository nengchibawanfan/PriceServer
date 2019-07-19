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
from priceserver.conf.settings import HUOBIPRO_API, COIN_BASE_URL, BYTETRADE_API, COIN_CURRENCY, CURRENCY_LIST

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
                self.r.hset("coinbase_currency_price", k, price)
        self.r.set("Receive_the_data_coinbase", time.time())

    def start(self):
        """
        维持quote字典最新
        :return:
        """
        logger.info("更新法币价格")
        self.pool.map(self.updateQuote, moneyLst)
        self.pool.close()
        self.pool.join()


if __name__ == '__main__':
    # 开始的时候将原来的键删掉，构建新的  一旦加了新的交易对，重启程序

    def push_bear():
        PUSH_BEAR_KEY = "11970-ba5f3d1644a4bd880a04ebdef3560f69"
        import requests
        url = "https://pushbear.ftqq.com/sub"
        data = {
            "sendkey": PUSH_BEAR_KEY,
            "text": "PriceServer——GraphQL",
            "desp": "coin_base数据获取超时五分钟"
        }
        headers = {
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "Accept-Encoding": "gzip, deflate, br",
            "User-Agent": "Mozilla/5.0 (Windows NT 6.1; WOW64; rv:47.0) Gecko/20100101 Firefox/47.0"}
        requests.post(url, data=data, headers=headers)


    push_bear()
    r = ConnectRedis()

    r.delete("coinbase_currency_price")

    obj = Quote()

    schedule.every(5).minutes.do(obj.start, "5min")

    while True:
        # try:
        schedule.run_pending()
