# -*- coding: utf-8 -*-
# Author: zhangchao
# Date: 2019-04-25
# Desc: 监控wss是否获取数据
import os

import redis
import time

r = redis.StrictRedis(decode_responses=True)


def push_bear():
    PUSH_BEAR_KEY = "11970-ba5f3d1644a4bd880a04ebdef3560f69"
    import requests
    url = "https://pushbear.ftqq.com/sub"
    data = {
        "sendkey": PUSH_BEAR_KEY,
        "text": "PriceServer——GraphQL",
        "desp": "没收到数据重启"
    }
    headers = {
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "Accept-Encoding": "gzip, deflate, br",
        "User-Agent": "Mozilla/5.0 (Windows NT 6.1; WOW64; rv:47.0) Gecko/20100101 Firefox/47.0"}
    requests.post(url, data=data, headers=headers)


while True:
    now = time.time()
    bytetrade_data = r.get("Receive_the_data_bytetrade")
    huobi_data = r.get("Receive_the_data_huobi")

    bytetrade = now - bytetrade_data
    huobi = now - huobi_data

    if bytetrade > 60 * 5:
        cmd_str = 'pm2 restart ' + "get_cu_price_and_sub_redis"

        result = os.system(cmd_str)

    if huobi > 60 * 5:
        cmd_str = 'pm2 restart ' + "get_cu_price_and_sub_redis"

        result = os.system(cmd_str)
