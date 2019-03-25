import graphene

from priceserver.cal_price import calculate_price
from priceserver.conf.settings import EXCHANGE_LIST, SYMBOL_LIST, CURRENCY_LIST
from priceserver.commen.logger import getLog

logger = getLog()

class Price(graphene.ObjectType):
    currency = graphene.String()
    price = graphene.Float()


class Symbol(graphene.ObjectType):
    symbol_name = graphene.String()
    price = graphene.List(Price)


class Exchange(graphene.ObjectType):
    exchange_name = graphene.String()
    coin_list = graphene.List(Symbol)


class Info(graphene.ObjectType):
    # info = graphene.List(Exchange)
    info = graphene.List(Exchange)


def _exchange(exchange_name, symbol, currency):

    if symbol:
        temp = symbol.split(",")
        symbol_list = [i.replace(" ", "") for i in temp]
    else:
        symbol_list = SYMBOL_LIST

    obj = Exchange(exchange_name=exchange_name,
                   coin_list=[_symbol(symbol_name=symbol_name, exchange_name=exchange_name, currency=currency) for
                              symbol_name in symbol_list]
                   )
    return obj


def _symbol(symbol_name, exchange_name, currency):
    if currency:
        temp = currency.split(",")
        currency_list = [i.replace(" ", "") for i in temp]
    else:
        currency_list = CURRENCY_LIST

    obj = Symbol(symbol_name=symbol_name,
                 price=[_price(currency=cu, symbol_name=symbol_name,
                               exchange_name=exchange_name) for cu in currency_list])

    return obj


def _price(currency, symbol_name, exchange_name):
    print(currency, symbol_name, exchange_name)
    start, mid = symbol_name.split("/")
    end = currency
    price = calculate_price(exchange_name, start, mid, end)

    return Price(currency=currency, price=price)


# 定义查询接口，类似于 GET
class Query(graphene.ObjectType):
    hello = graphene.String()

    def resolve_hello(self, info, **kwargs):

        return "THIS IS PRICE_SERVER"

    # 查询接口以及必须的参数
    # graphene.String(required=True)
    price_server = graphene.Field(Info, exchange_name=graphene.String(),
                                  symbol=graphene.String(),
                                  currency=graphene.String())

    # exchange = graphene.List(Exchange)
    # symbol = graphene.List(Symbol)
    # price = graphene.Field(Price)

    def resolve_price_server(self, info, exchange_name=None, symbol=None, currency=None):

        if exchange_name:
            temp = exchange_name.split(",")
            exchange_list = [i.replace(" ", "") for i in temp]

        else:
            exchange_list = EXCHANGE_LIST

        obj = Info(
            info=[_exchange(exchange_name=ex, symbol=symbol, currency=currency) for ex in
                  exchange_list]
        )

        return obj



if __name__ == '__main__':
    pass
