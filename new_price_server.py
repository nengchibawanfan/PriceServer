# -*- coding: utf-8 -*
from flask import Flask
from flask_graphql import GraphQLView
from werkzeug.contrib.fixers import ProxyFix

from priceserver.schema import schema

app = Flask(__name__)
app.debug = True
app.add_url_rule("/graphql", view_func=GraphQLView.as_view("graphql", schema=schema, graphiql=True))


def push_bear():
    import requests
    url = "https://pushbear.ftqq.com/sub"
    data = {
        "sendkey": "11970-ba5f3d1644a4bd880a04ebdef3560f69",
        "text": "PriceServer——GraphQL",
        "desp": "报价服务重启！快去看看为啥！"
    }
    headers = {
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "Accept-Encoding": "gzip, deflate, br",
        "User-Agent": "Mozilla/5.0 (Windows NT 6.1; WOW64; rv:47.0) Gecko/20100101 Firefox/47.0"}
    requests.post(url, data=data, headers=headers)


if __name__ == '__main__':
    # 该做的都做了，启动服务
    push_bear()
    # 在这里加一个启动短信提醒

    app.wsgi_app = ProxyFix(app.wsgi_app)
    app.run(host="0.0.0.0", port="5000", debug=False, threaded=True)
