# -*- coding: utf-8 -*-
# Author: zhangchao
# Date: 2019-04-10
# Desc: 报价服务入口，Flask-app
import json
import os
import time

from flask import Flask, request
from flask_graphql import GraphQLView
from werkzeug.contrib.fixers import ProxyFix

from priceserver.schema import schema
from priceserver.common.db_connection import ConnectRedis
from priceserver.common.tools import get_market_id_num_mapping

app = Flask(__name__)
app.debug = True
app.add_url_rule("/graphql", view_func=GraphQLView.as_view("graphql", schema=schema, graphiql=True))
app.secret_key = 'bytetrade' + str(time.time()) + str(os.urandom(24))  # 配置secret_key,否则不能实现session对话  随机值更好

r = ConnectRedis()
MARKET_ID_NUM_MAPPING = get_market_id_num_mapping()

@app.route("/next_price")
def get_next_price():

    response = {}
    response["code"] = 200
    response["price"] = {}
    marketids = request.args.getlist('marketids')
    for marketid in marketids:


        next_price = r.hget("next_price", MARKET_ID_NUM_MAPPING[marketid])
        response["price"][marketid] = next_price

    return json.dumps(response)

    pass

if __name__ == '__main__':
    # 该做的都做了，启动服务
    # push_bear()
    # 在这里加一个启动短信提醒

    # app.wsgi_app = ProxyFix(app.wsgi_app)
    app.run(host="0.0.0.0", port="5006", debug=False, threaded=True)
