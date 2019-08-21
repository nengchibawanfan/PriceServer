import json
import random
import time

import graphene

from priceserver.cal_price import CalPrice
from priceserver.common.db_connection import ConnectRedis
from priceserver.conf.settings import SYMBOL_LIST, CURRENCY_LIST
from priceserver.common.logger import getLog

r = ConnectRedis()
logger = getLog()

class Price(graphene.ObjectType):
    currency = graphene.String()
    price = graphene.Float()


class Symbol(graphene.ObjectType):
    symbol_name = graphene.String()
    today = graphene.String()
    price = graphene.List(Price)

class Today(graphene.ObjectType):
    symbol_name = graphene.String()
    today = graphene.String()


def create_symbol_obj(symbol_name, currency, calprice):

    if "/" in symbol_name:
        # 看是MT/ETH这种,还是MT这种    获取这个的today 勇哥那边就不需要再查了
        today = r.hget("price_server_bytetrade_today1", symbol_name)
    else:
        today = ""

    obj = Symbol(symbol_name=symbol_name, today=today, price=[create_price_obj(symbol_name, i, calprice) for i in currency])

    return obj

def create_price_obj(symbol_name, currency, calprice):

    if "/" in symbol_name:

        symbol = symbol_name
        start, mid = symbol.split("/")
        price = calprice.calculate_price(start, currency, mid)

    else:
        # 优先计算兑ETH
        price = calprice.calculate_price(symbol_name, currency)

    # price = random.randrange(1000)
    obj = Price(currency=currency, price=price)
    return obj


# 定义查询接口，类似于 GET
class Query(graphene.ObjectType):
    hello = graphene.String()

    def resolve_hello(self, info, **kwargs):

        return "THIS IS PRICE_SERVER"

    # 查询接口以及必须的参数
    # graphene.String(required=True)
    symbols = graphene.List(Symbol, symbol_name=graphene.String(), currency=graphene.String())

    def resolve_symbols(self, info, symbol_name=None, currency=None, **kwargs):

        key_bytetrade = "price_server_bytetrade1"
        key_huobipro = "price_server_huobipro1"
        key_coin_base = "coinbase_currency_price1"
        key_path_price = "price_server_path_price1"

        r = ConnectRedis()

        bytetrade_price = r.hgetall(key_bytetrade)
        huobi_price = r.hgetall(key_huobipro)
        coinbase_price = r.hgetall(key_coin_base)
        path_price = r.hgetall(key_path_price)

        calprice = CalPrice(bytetrade_price, huobi_price, coinbase_price, path_price)

        if currency:
            # 传来的法币是一个字符串  用,分割
            temp = currency.split(",")
            currency_list = [i.replace(" ", "") for i in temp]
        else:
            # 没传就返回所有的法币价格
            currency_list = CURRENCY_LIST

        if symbol_name:
            # 如果传了市场的列表 分割
            temp = symbol_name.split(",")
            symbol_list = [i.replace(" ", "") for i in temp]
        else:
            symbol_list = SYMBOL_LIST
            # symbol_list = MARKET_LIST
            # all 就是我们交易所目前支持的所有的币对
            # 返回所有
        t1 = time.time()
        res = [create_symbol_obj(i, currency_list, calprice)for i in symbol_list]
        print(time.time() - t1)
        return res

    all_price = graphene.String()
    def resolve_all_price(self, info, **kwargs):
        res = r.get("price_cache")

        return res

    all_today = graphene.List(Today)
    def resolve_all_today(self, info):

        response = []
        res = r.hgetall("price_server_bytetrade_today1")
        for k, v in res.items():
            obj = Today(symbol_name=k, today=v)
            response.append(obj)
        return response

if __name__ == '__main__':
    pass
