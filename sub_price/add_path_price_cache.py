# -*- coding: utf-8 -*-
# Author: zhangchao
# Date: 2019-08-20
# Desc:

import time

import requests

# -*- coding: utf-8 -*-
# Author: zhangchao
# Date: 2019-08-15
# Desc: 从graphql获取法币的价格    保存在redis中，随时查

import sys
import time

import requests

from priceserver.common.db_connection import ConnectRedis

sys.path.append("../..")


r = ConnectRedis()

def job():
    url = "http://3.92.180.68:5005/graphql?"
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
    requests.post(url, params).content.decode("utf8")



if __name__ == '__main__':

    import schedule


    schedule.every(5).minutes.do(job)

    while True:
        # try:
        schedule.run_pending()
        time.sleep(60)

