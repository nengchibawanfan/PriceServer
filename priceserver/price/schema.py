import graphene

from priceserver.cal_price import calculate_price
from utils.logger import getLog

logger = getLog()


class Price(graphene.ObjectType):
    currency = graphene.String()
    price = graphene.Float()


class Symbol(graphene.ObjectType):
    symbol = graphene.String()
    price = graphene.List(Price)


class Exchange(graphene.ObjectType):
    exchange_name = graphene.String()
    coin_list = graphene.List(Symbol)


class Info(graphene.ObjectType):
    # info = graphene.List(Exchange)
    info = graphene.List(Exchange)


response = {
    "info": [
        {
            "exchange_name": "huobipro",
            "coin_list": [{"coin_name": "MT/ETH",
                           "price": [{
                               "currency": "CNY",
                               "price": 1000
                           },
                               {
                                   "currency": "USD",
                                   "price": 1000
                               }]},
                          {"coin_name": "MT/BTC",
                           "price": [{
                               "currency": "CNY",
                               "price": 1000
                           },
                               {
                                   "currency": "USD",
                                   "price": 1000
                               }]}
                          ],
        },
        {
            "exchange_name": "bytetrade",
            "coin_list": [{"coin_name": "MT/ETH",
                           "price": [{
                               "currency": "CNY",
                               "price": 1000
                           },
                               {
                                   "currency": "USD",
                                   "price": 1000
                               }]},

                          {"coin_name": "MT/ETH",
                           "price": [{
                               "currency": "CNY",
                               "price": 1000
                           },
                               {
                                   "currency": "USD",
                                   "price": 1000
                               }]}
                          ],

        },
        {
            "exchange_name": "okex",
            "coin_list": [{"coin_name": "MT/ETH",
                           "price": [{
                               "currency": "CNY",
                               "price": 1000
                           },
                               {
                                   "currency": "USD",
                                   "price": 1000
                               }]},
                          {"coin_name": "MT/ETH",
                           "price": [{
                               "currency": "CNY",
                               "price": 1000
                           },
                               {
                                   "currency": "USD",
                                   "price": 1000
                               }]}
                          ],
        }]
}


# 定义查询接口，类似于 GET
class Query(graphene.ObjectType):
    hello = graphene.String()

    def resolve_hello(self, info, **kwargs):
        return "hello"

    # 查询接口以及必须的参数
    info = graphene.Field(Info)
    exchange = graphene.List(Exchange, exchange_name=graphene.String(required=True))
    symbol = graphene.List(Symbol, symbol=graphene.String(required=True))
    price = graphene.List(Price, currency=graphene.String(required=True), symbol_name=graphene.String(required=True),
                          exchange_name=graphene.String(required=True))

    def resolve_info(self, info, *args, **kwargs):
        # obj = Info(
        #     info=[self.resolve_exchange(info, exchange_name=exchange_name) for exchange_name in
        #           ["huobipro", "bytetrade"]]
        # )
        obj = Info(info="aaaaa")

        return obj

    def resolve_exchange(self, info, exchange_name):
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

    def resolve_price(self, info, currency, symbol_name, exchange_name):
        start, mid = symbol_name.split("/")
        end = currency
        price = calculate_price(exchange_name, start, mid, end)

        return Price(currency=currency, price=price)


if __name__ == '__main__':
    pass
