# -*- coding: utf-8 -*-
# Author: zhangchao
# Date: 2019-08-15
# Desc: 从graphql获取法币的价格    保存在redis中，随时查
import json
import sys
import time

import requests

sys.path.append("..")
from priceserver.common.db_connection import ConnectRedis
from priceserver.common.tools import get_all_markets_name

MARKET_LIST = get_all_markets_name()

market_list = ""

for i in MARKET_LIST:
    market_list += i
    market_list += ","

r = ConnectRedis()


def job():
    url = "http://127.0.0.1:5000/graphql?"
    params = {
        "query": """query{
      symbols{
        symbolName
        price {
          currency
          price
        }
      }
    }"""
    }
    response = eval(requests.post(url, params).content.decode("utf8"))
    # print(response["data"]["symbols"])
    data = str(response["data"]["symbols"])
    print(response)
    r.set("price_cache", data)
    s = ""

    s += 'query{symbols(symbolName:"'
    s += market_list
    s += '") { symbolName  price {currency  price}}}'

    params = {
        "query": s
    }
    response = eval(requests.post(url, params).content.decode("utf8"))
    print(response["data"]["symbols"])
    data = str(response["data"]["symbols"])
    r.set("price_market_cache", data)


if __name__ == '__main__':

    import schedule

    # job()
    #

    schedule.every(5).minutes.do(job)

    while True:
        # try:
        schedule.run_pending()
        time.sleep(60)
