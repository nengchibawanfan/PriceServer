# -*- coding: utf-8 -*-
# Author: zhangchao
# Date: 2019-07-18
# Desc: 监控获取价格是否正常，不正常，就重启
import datetime
import sys
sys.path.append("..")
import os
import redis
import time

r = redis.StrictRedis(decode_responses=True)

while True:
    now = time.time()
    bytetrade_data = float(r.get("Receive_the_data_bytetrade1"))
    huobi_data = float(r.get("Receive_the_data_huobi1"))
    coinbase_data = float(r.get("Receive_the_data_coinbase1"))
    price_server_path_price_alive_data = float(r.get("price_server_path_price_alive1"))

    bytetrade = now - bytetrade_data
    huobi = now - huobi_data
    coinbase = now - coinbase_data
    price_server_path_price_alive = now - price_server_path_price_alive_data

    if bytetrade > 60 * 5:
        cmd_str = 'pm2 restart ' + "sub_bytetrade_price"

        result = os.system(cmd_str)
        print(datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        print("重启bytetrade")


    if huobi > 60 * 5:
        cmd_str = 'pm2 restart ' + "sub_huobi_price"

        result = os.system(cmd_str)
        print(datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'))

        print("重启huobipro")


    if coinbase > 60 * 5:
        cmd_str = 'pm2 restart ' + "get_coinbase_price"

        result = os.system(cmd_str)
        print(datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'))

        print("重启coinbase")

    if coinbase > 60 * 5:
        cmd_str = 'pm2 restart ' + "add_path_price_catch"

        result = os.system(cmd_str)
        print(datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'))

        print("重启缓存")

    time.sleep(60 * 3)
