# -*- coding: utf-8 -*-
# Author: zhangchao
# Date: 2019-04-25
# Desc: 监控wss是否获取数据
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
        cmd_str = 'pm2 restart ' + "get_cu_price_and_sub_redis"

        result = os.system(cmd_str)

    if huobi > 60 * 5:
        cmd_str = 'pm2 restart ' + "get_cu_price_and_sub_redis"

        result = os.system(cmd_str)

    if coinbase > 60 * 5:
        cmd_str = 'pm2 restart ' + "get_cu_price_and_sub_redis"

        result = os.system(cmd_str)
