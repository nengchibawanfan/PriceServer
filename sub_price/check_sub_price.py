# -*- coding: utf-8 -*-
# Author: zhangchao
# Date: 2019-07-18
# Desc: 监控获取价格是否正常，不正常，就重启


import sys
sys.path.append("..")
import os
import redis
import time

r = redis.StrictRedis(decode_responses=True)

while True:
    now = time.time()
    bytetrade_data = float(r.get("Receive_the_data_bytetrade"))
    huobi_data = float(r.get("Receive_the_data_huobi"))
    coinbase_data = float(r.get("Receive_the_data_coinbase"))

    bytetrade = now - bytetrade_data
    huobi = now - huobi_data
    coinbase = now - coinbase_data

    if bytetrade > 60 * 5:
        cmd_str = 'pm2 restart ' + "sub_bytetrade_price"

        result = os.system(cmd_str)

    if huobi > 60 * 5:
        cmd_str = 'pm2 restart ' + "sub_huobi_price"

        result = os.system(cmd_str)

    if coinbase > 60 * 5:
        cmd_str = 'pm2 restart ' + "get_coinbase_price"

        result = os.system(cmd_str)
    time.sleep(60 * 3)
