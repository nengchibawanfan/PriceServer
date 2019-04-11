import random

import graphene

from priceserver.cal_price import calculate_price
from priceserver.conf.settings import SYMBOL_LIST, MARKET_LIST, CURRENCY_LIST, PRIORITY
from priceserver.common.logger import getLog

logger = getLog()

class Price(graphene.ObjectType):
    currency = graphene.String()
    price = graphene.Float()


class Symbol(graphene.ObjectType):
    symbol_name = graphene.String()
    price = graphene.List(Price)

def create_symbol_obj(symbol_name, currency):
    obj = Symbol(symbol_name=symbol_name, price=[create_price_obj(symbol_name, i) for i in currency])

    return obj

def create_price_obj(symbol_name, currency):
    if "/" in symbol_name:
        symbol = symbol_name
    else:
        symbol = symbol_name + "/" + PRIORITY[0]


    start, mid = symbol.split("/")
    price = calculate_price(start, mid, currency)
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
        if currency:
            temp = currency.split(",")
            currency_list = [i.replace(" ", "") for i in temp]
        else:
            currency_list = CURRENCY_LIST
        # 返回所有的

        if symbol_name:
            temp = symbol_name.split(",")
            symbol_list = [i.replace(" ", "") for i in temp]

        else:
            pass
            symbol_list = SYMBOL_LIST
            # symbol_list = MARKET_LIST
            # all 就是我们交易所目前支持的所有的币对
            # 返回所有

        return [create_symbol_obj(i, currency_list)for i in symbol_list]

    all_price = graphene.List(Price, currency=graphene.String())
    def resolve_all_price(self, info, currency, **kwargs):
        pass


if __name__ == '__main__':
    pass
