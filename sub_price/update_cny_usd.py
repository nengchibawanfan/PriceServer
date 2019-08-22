# -*- coding: utf-8 -*-
# Author: zhangchao
# Date: 2019-08-22
# Desc: 更新CNY和USD频率要快

import json
import sys
import time

import requests


sys.path.append("..")
from priceserver.conf.settings import MARKET_LIST
from priceserver.common.db_connection import ConnectRedis


market_list = ""

for i in MARKET_LIST:
    market_list += i
    market_list += ","




r = ConnectRedis()

def job():
    url = "http://127.0.0.1:5000/graphql?"
    params = {
        "query": """query{
      symbols (currency: "USD, CNY"){
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
    data = eval(str(response["data"]["symbols"]))
    temp = {}
    for i in data:
        temp[i["symbolName"]] = {}
        for j in i["price"]:
            temp[i["symbolName"]][j["currency"]] = j["price"]


    res = eval(r.get("price_cache"))
    print(res)


    temp_lst = []

    for i in res:
        symbolName = i["symbolName"]
        CNY = temp[symbolName]["CNY"]
        USD = temp[symbolName]["USD"]
        for j in i["price"]:
            if j["currency"] == "CNY":
                j["price"] = CNY
            elif j["currency"] == "USD":
                j["price"] = USD
            else:
                pass
        temp_lst.append(i)

    r.set("price_cache", str(temp_lst))

    # #

    s = ""

    s += 'query{symbols(symbolName:"'
    s += market_list
    s += '", currency: "USD, CNY") { symbolName  price {currency  price}}}'

    params = {
        "query": s
    }
    response = eval(requests.post(url, params).content.decode("utf8"))
    data = eval(str(response["data"]["symbols"]))
    temp = {}
    for i in data:
        temp[i["symbolName"]] = {}
        for j in i["price"]:
            temp[i["symbolName"]][j["currency"]] = j["price"]

    res = eval(r.get("price_market_cache"))


    temp_lst = []

    for i in res:
        symbolName = i["symbolName"]
        CNY = temp[symbolName]["CNY"]
        USD = temp[symbolName]["USD"]
        for j in i["price"]:
            if j["currency"] == "CNY":
                j["price"] = CNY
            elif j["currency"] == "USD":
                j["price"] = USD
            else:
                pass
        temp_lst.append(i)

    r.set("price_market_cache", str(temp_lst))




if __name__ == '__main__':


    while True:
        # try:
        job()

        time.sleep(30)
