# -*- coding: utf-8 -*
import graphene

from FlaskWeb.PriceServer.price import schema
from FlaskWeb.PriceServer import price


# 总的schema入口

class Query(price.schema.Query, graphene.ObjectType):
    # 总的Schema的query入口
    pass


class Mutations(graphene.ObjectType):
    # 总的Schema的mutations入口
    pass


schema = graphene.Schema(query=Query)
