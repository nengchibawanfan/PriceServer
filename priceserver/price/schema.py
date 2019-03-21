import sys

import graphene

sys.path.append("../..")

from FlaskWeb.PriceServer.cal_price import calculate_price


class Price(graphene.ObjectType):
    currency = graphene.String()
    price = graphene.String()


class Symbol(graphene.ObjectType):
    name = graphene.String()
    info = graphene.List(Price)


class Exchange(graphene.ObjectType):
    name = graphene.String()
    symbols = graphene.List(Symbol)


class Account(graphene.ObjectType):
    name = graphene.String()
    age = graphene.Int()
    sex = graphene.String()
    department = graphene.String()


class CurrencyPrice(graphene.ObjectType):
    coin_name = graphene.String()
    exchange = graphene.String()
    currency = graphene.String()
    price = graphene.Float()


# 定义查询接口，类似于 GET
class Query(graphene.ObjectType):
    hello = graphene.String()

    def resolve_hello(self, info, **kwargs):
        print(info)
        print(kwargs)
        return "hello"

    currency_price = graphene.Field(CurrencyPrice, coin_name=graphene.String(required=True),
                                    exchange=graphene.String(required=True), currency=graphene.String(required=True))

    def resolve_currency_price(self, info, coin_name, exchange, currency):
        price = calculate_price(exchange, coin_name, currency)

        return CurrencyPrice(coin_name=coin_name, exchange=exchange, currency=currency, price=price)


if __name__ == '__main__':
    pass
