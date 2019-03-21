
# -*- coding: utf-8 -*
import sys

from flask import Flask
from flask_graphql import GraphQLView
from werkzeug.contrib.fixers import ProxyFix

sys.path.append("../..")

from FlaskWeb.PriceServer.schema import schema

app = Flask(__name__)
app.debug = True
app.add_url_rule("/graphql", view_func=GraphQLView.as_view("graphql", schema=schema, graphiql=True))

if __name__ == '__main__':
    # 该做的都做了，启动服务
    app.wsgi_app = ProxyFix(app.wsgi_app)
    app.run(host="0.0.0.0", port="5000", debug=False, threaded=True)
