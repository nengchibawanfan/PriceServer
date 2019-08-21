# -*- coding: utf-8 -*-
# Author: zhangchao
# Date: 2019-08-15
# Desc: 从graphql获取法币的价格    保存在redis中，随时查

import sys
import time

import requests

sys.path.append("..")
from priceserver.common.db_connection import ConnectRedis



r = ConnectRedis()

def job():
    url = "http://127.0.0.1:5005/graphql?"
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



if __name__ == '__main__':

    import schedule
    job()


    schedule.every(1).minutes.do(job)

    while True:
        # try:
        schedule.run_pending()
        time.sleep(60)
