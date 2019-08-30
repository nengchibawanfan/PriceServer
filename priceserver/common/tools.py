# -*- coding: utf-8 -*-
# Author: zhangchao
# Date: 2019-08-29
# Desc:
import json
import re

import requests

from priceserver.conf.settings import configs

BYTETRADE_API = configs["exchange"]["bytetrade"]["restful_url"]

params = {"cmd": "marketsPrice",
          "channel": "ALL"}
res = eval(requests.get(BYTETRADE_API, params=params).content.decode("utf-8"))


# 获取交易所支持的所有市场的id
def get_all_markets_id():
    """
    获取交易所有的市场
    :return:    str
         "2147483649"
    """
    markets = list(set([str(i["id"]) for i in res["result"]]))

    return markets


# 获取交易所支持的所有市场的name
def get_all_markets_name():
    """
    获取交易所有的市场
    :return: "MT/ETH"
    """

    markets = list(set([str(i["name"]) for i in res["result"]]))

    return markets


# 获取交易所支持的所有市场的num
def get_all_markets_num():
    """
    获取交易所有的市场
    :return: "5/2"
    """

    markets = list(set([str(i["stockId"]) + "/" + str(i["moneyId"]) for i in res["result"]]))

    return markets


# 获取id和coinname的映射  balance
def get_balance_id_name_mapping():
    """
    获取id：coinname的映射
    id  类型为int
    :return:
    """
    mapping = {}

    for i in res["result"]:
        stock_name, money_name = i["name"].split("/")
        stock_id = str(i["stockId"])
        money_id = str(i["moneyId"])
        mapping[stock_id] = stock_name
        mapping[money_id] = money_name

    return mapping


# 获取coinname id的映射
def get_balance_name_id_mapping():
    """
    获取id：coinname的映射
    id  类型为int
    :return:
    """
    mapping = {}

    for i in res["result"]:
        stock_name, money_name = i["name"].split("/")
        stock_id = i["stockId"]
        money_id = i["moneyId"]
        mapping[stock_name] = str(stock_id)
        mapping[money_name] = str(money_id)
    mapping["CMT"] = 18
    return mapping


# 获取数字类型市场与名字的映射
def get_market_num_name_mapping():
    result = {str(i["stockId"]) + "/" + str(i["moneyId"]): i["name"] for i in res["result"] if i["moneyId"] != 1}
    return result


def get_market_num_id_mapping():
    result = {str(i["stockId"]) + "/" + str(i["moneyId"]): str(i["id"]) for i in res["result"] if i["moneyId"] != 1}
    return result


# 获取市场id与名字的映射
def get_market_id_name_mapping():
    result = {str(i["id"]): i["name"] for i in res["result"] if i["moneyId"] != 1}

    return result


def get_market_id_num_mapping():
    result = {str(i["id"]): str(i["stockId"]) + "/" + str(i["moneyId"]) for i in res["result"] if i["moneyId"] != 1}

    return result


# 获取市场id与名字的映射
def get_market_name_id_mapping():
    result = {i["name"]: str(i["id"]) for i in res["result"] if i["moneyId"] != 1}

    return result


def get_market_name_num_mapping():
    result = {i["name"]: str(i["stockId"]) + "/" + str(i["moneyId"]) for i in res["result"] if i["moneyId"] != 1}
    return result


def parse_json(json_str):
    # 处理// ... /n 格式非json内容
    json_str1 = re.sub(re.compile('(//\s[\\s\\S]*?\n)'), '', json_str)
    # # 处理/*** ... */ 格式非json内容
    json_str2 = re.sub(re.compile('(/\*\*\*[\\s\\S]*?/)'), '', json_str1)

    # 返回json格式的数据
    return json.loads(json_str2)


if __name__ == '__main__':
    # print(get_all_markets_id())
    # print(get_all_markets_name())
    # print(get_all_markets_num())
    # print(get_balance_id_name_mapping())
    # print(get_balance_name_id_mapping())
    # print(get_market_num_name_mapping())
    # print(get_market_num_id_mapping())
    # print(get_market_id_name_mapping())
    print(get_market_id_num_mapping())
    # print(get_market_name_id_mapping())
    # print(get_market_name_num_mapping())
