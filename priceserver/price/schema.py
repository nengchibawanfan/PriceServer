import graphene

from priceserver.cal_price import calculate_price
from utils.logger import getLog

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

def fetch_info():
    pass

def  fetch_exchange_by_exchange_name(exchange_name):
    pass

def fetch_symbol_by_ccxt_symbol(symbol):
    pass

def fetch_price(currency, symbol):
    pass


def _exchange(exchange_name=None):
    if exchange_name:
        # 解析exhangename
        exchange_name = [exchange_name]
    else:
        exchange_name = ["huobipro", "bytetrade", "okex"]

    for exchange in exchange_name:
        obj = Exchange(exchange_name=exchange_name,
                       coin_list=[_symbol(symbol_name=symbol_name, exchange_name=exchange) for
                                  symbol_name in ["MT/ETH", "KCASH/ETH"]]
                       )
        return obj

def _symbol(symbol_name, exchange_name):
    obj = Symbol(symbol_name=symbol_name,
                 price=[_price(currency=currency, symbol_name=symbol_name,
                                            exchange_name=exchange_name) for currency in ["CNY", "USD"]])

    return obj

def _price(currency, symbol_name, exchange_name):

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
    info = graphene.Field(Info)
    exchange = graphene.List(Exchange)
    symbol = graphene.List(Symbol)
    price = graphene.Field(Price)

    def resolve_info(self, info, *args, **kwargs):
        obj = Info(
            info=[_exchange(exchange_name=exchange_name) for exchange_name in
                  ["huobipro", "bytetrade"]]
        )
        # obj = Info()
        #
        return obj

    def resolve_exchange(self, info, exchange_name=None):
        # if exchange_name:
        #     # 解析exhangename
        #     exchange_name = [exchange_name]
        # else:
        #     exchange_name = ["huobipro", "bytetrade", "okex"]

        for exchange in exchange_name:
            obj = Exchange(exchange_name=exchange_name,
                           coin_list=[self.resolve_symbol(info, symbol_name=symbol_name, exchange_name=exchange_name) for
                                      symbol_name in ["MT/ETH", "KCASH/ETH"]]
                           )
            return obj

    def resolve_symbol(self, info, symbol_name, exchange_name):
        obj = Symbol(symbol_name=symbol_name,
                     price=[self.resolve_price(info, currency=currency, symbol_name=symbol_name,
                                               exchange_name=exchange_name) for currency in ["CNY", "USD"]])

        return obj

    def resolve_price(self, info, currency="CNY", symbol_name="MT/ETH", exchange_name="bytetrade"):

        start, mid = symbol_name.split("/")
        end = currency
        price = calculate_price(exchange_name, start, mid, end)

        return Price(currency=currency, price=price)


if __name__ == '__main__':
    pass
