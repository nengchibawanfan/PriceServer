import logging

import json
import requests
import redis

from threading import Lock
import multiprocessing.dummy
from retry import retry

from flask import Flask, request, render_template
from flask_socketio import SocketIO

from FlaskWeb.PriceServer.conf.settings import BYTETRADE_API, BYTETRADE_TEST_API

logger = logging.getLogger(__name__)
logger.setLevel(level=logging.INFO)
handler = logging.FileHandler("./logs/price_server.logs")
handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)

console = logging.StreamHandler()
console.setLevel(logging.INFO)

logger.addHandler(handler)
logger.addHandler(console)


def get_cion_id_mapping():
    """
    回去coin id 的映射字典
    :return:
    """
    url = BYTETRADE_API + "?cmd=markets"
    res = eval(requests.get(url).content.decode("utf-8"))
    mapping = {i["stockId"]: i["stock"] for i in res["symbols"]}
    symbols = res["symbols"]

    return mapping, symbols


ID_COIN_MAPPING, MARKETIDS = get_cion_id_mapping()

COIN_ID_MAPPING = dict(zip(ID_COIN_MAPPING.values(), ID_COIN_MAPPING.keys()))

baseId = 2147483647


class Market(object):

    def __init__(self, market):
        self.symbol = market["name"]  # BTT/ETH
        self.stock = market["stock"]  # BTT
        self.stockId = market["stockId"]  # 2 int
        self.money = market["money"]  # ETH
        self.moneyId = market["moneyId"]  # 6 int
        self.marketId = market["id"]  # marketId
        self.lastPrice = None


class QuoteServer():
    def __init__(self):
        self.r = redis.StrictRedis(decode_responses=True)
        self.s1 = set()  # 集合一
        self.s2 = set()  # 集合二  50
        self.s3 = set()  # 集合二  相反数
        # self.getMarkets()
        self.markets = MARKETIDS
        self.pool = multiprocessing.dummy.Pool()
        self.result = {}

    def calculatePrice(self, price, marketPrice):
        return float(price) * float(marketPrice)

    @retry(10, 3)
    def sendRequest(self, url, params=None):
        if params:
            response = requests.get(url, params).content.decode("utf-8")
        else:
            response = requests.get(url).content.decode("utf-8")
        return response

    def updateMarkets(self):
        url = BYTETRADE_TEST_API + "?cmd=markets"
        res = self.sendRequest(url)
        self.markets = json.loads(res)["symbols"]

    def getMidPrice(self, moneyId, marketId):
        """
        不能直接计算价格，需要中间价格
        :param moneyId: 6
        :param marketId:
        :return: 2， price
        """
        # 判断与moneyId的交易对 此时moneyId作为stockId
        for market in self.markets:
            if (market["id"] - moneyId) / 2147483647 != 0 and (market["id"] - moneyId) % 2147483647 == 0:
                self.s1.add(market["money"])
        r = eval(self.r.hget("quote", currency)).keys()
        self.s2 = set(list(r))
        if self.s1:
            # 取交集
            commenSet = self.s1 & self.s2

            if commenSet:
                if "ETH" in commenSet:
                    # 有没有KCASH/ETH
                    marketId = 2147483647 * 2 + moneyId
                    # 获取该币种与ETH的报价
                    try:
                        midPrice = float(self.r.lindex(marketId, -1))
                        return 2, midPrice
                    except Exception as e:
                        logger.info(e)
                        return 2, 0

                # elif "BTC" in commenSet:
                #     pass
                #
                #

                else:
                    # 没有与ETH的就瞎选一个
                    x = commenSet.pop()
                    xId = COIN_ID_MAPPING[x]
                    marketId = 2147483647 * int(xId) + moneyId
                    try:
                        midPrice = self.r.lindex(marketId, -1)
                        return int(xId), float(midPrice)
                    except Exception as e:
                        logger.info(e)
                        return xId, 0
            else:
                logger.info("没有commenSet  转换后币种的报价")
                return 0, None
        else:
            logger.info("寻找moneyId作为moneyId的其他交易对")
            for market in self.markets:
                if market["id"] != marketId and market["id"] // baseId == moneyId:
                    # stockId = market["id"] % baseId
                    self.s3.add(market["stock"])

            commenSet = self.s3 & self.s2

            if commenSet:
                if "ETH" in commenSet:
                    # 有没有KCASH/ETH
                    marketId = 2147483647 * moneyId + 2
                    # 获取该币种与ETH的报价
                    midPrice = float(self.r.lindex(marketId, -1))
                    return 2, 1 / midPrice

                else:
                    # 没有与ETH的就瞎选一个
                    x = commenSet.pop()
                    xId = COIN_ID_MAPPING[x]
                    marketId = 2147483647 * moneyId + int(xId)
                    try:
                        midPrice = self.r.lindex(marketId, -1)
                        return int(xId), 1 / float(midPrice)
                    except:
                        return xId, None
            else:
                logger.info("没有commenSet  转换后币种的报价")
                return 0, None

    def getcuPrice(self, symbolId, currency):
        """
        获取法币价格
        :param symbolId: （ETH）  2
        :param currency: CNY
        :return: 法币价格
        """
        # 获取法币价格
        if currency in self.r.hkeys("quote"):
            # 已经有缓存的法币对各种币的价格 CNY USD
            value = eval(self.r.hget("quote", str(currency)))  # dict
            if symbolId in ID_COIN_MAPPING and ID_COIN_MAPPING[symbolId] in value:
                # 有直接兑换的交易对 比如 ETH/CNY
                price = value[ID_COIN_MAPPING[symbolId]]
                return price
        else:
            logger.info(f"redis法币{currency}数据已经超过一分钟未更新，请检查获取法币价格服务")
            return None

    def getMarketPrice(self, stockId, moneyId, exchange):
        # 获取market价格
        marketId = int(moneyId) * 2147483647 + int(stockId)
        try:
            lastPrice = float(self.r.get("price_server_" + exchange + str(marketId)))
        except:
            logger.info("没有将该币对缓存到redis中")
            lastPrice = None
        return lastPrice

    def verifyMarketId(self, marketId):
        for market in self.markets:
            if int(market["id"]) == int(marketId):
                return market
        else:
            return None

    def start(self, marketId, exchange, currency):
        m = self.verifyMarketId(marketId)
        if m:
            market = Market(m)
            # 获取marketPrice
            market.lastPrice = self.getMarketPrice(market.stockId, market.moneyId, exchange)

            if market.lastPrice:
                # 查询法币价格
                cuPrice = self.getcuPrice(market.moneyId, currency)

                if cuPrice:
                    self.result[currency][market.symbol] = self.calculatePrice(market.lastPrice, cuPrice)
                else:
                    # 没有直接兑换的 ，需要中间值
                    midId, midPrice = self.getMidPrice(market.moneyId, market.marketId)
                    cuPrice = self.getcuPrice(midId, currency)
                    self.result[currency][market.symbol] = self.calculatePrice(float(market.lastPrice) * midPrice,
                                                                               cuPrice)
            else:
                # logs.info(f"{market.symbol}在ByteTrade当前报价为0")
                self.result[currency][market.symbol] = 0

        else:
            logger.info(f"没有查到该交易对，marketId{marketId}输入错误或markets列表未更新...")
            self.updateMarkets()
            logger.info(f"更新markets列表。。。。。。。")
            m = self.verifyMarketId(marketId)
            if m:
                market = Market(m)
                # 获取marketPrice
                market.lastPrice = self.getMarketPrice(market.stockId, market.moneyId)
                if market.lastPrice:
                    # 查询法币价格
                    cuPrice = self.getcuPrice(market.moneyId, currency)
                    if cuPrice:
                        self.result[currency][market.symbol] = self.calculatePrice(market.lastPrice, cuPrice)
                else:
                    logger.info(f"{market.symbol}在ByteTrade当前报价为0")
                    self.result[currency][market.symbol] = 0
            else:
                logger.info(f"marketId{marketId}输入错误，请检查后输入")
        return self.result

    def go(self, marketIdList, exchange, currency):
        # symbol = "4294967297"
        self.result[currency] = {}
        for marketId in marketIdList:
            self.pool.apply_async(self.start, (marketId, exchange, currency))
        self.pool.close()
        self.pool.join()
        return self.result


app = Flask(__name__)
socketio = SocketIO(app)

async_mode = None
thread = None
thread_lock = Lock()


@app.route('/')
def index():
    return render_template('index.html')


@app.route("/priceServer", methods=["POST"])
def priceServer():
    if request.method == 'POST':
        # global currency
        marketIds = request.form.get('marketIds')
        exchange = request.form.get('exchange')
        currency = request.form.get('currency')
        # marketIdList = marketIds.split(",").replace(" ", "")
        marketIdList = [marketid.replace(" ", "") for marketid in marketIds.split(",")]
        qs = QuoteServer()
        return json.dumps(qs.go(marketIdList, exchange, currency))


@socketio.on('priceServer', namespace='/wsPriceServer')
def wsPriceServer(data):
    global currency
    global thread
    currency = data.get("currency")
    exchange = data.get("exchange")
    marketIds = data.get("marketIds")
    with thread_lock:
        if thread is None:
            thread = socketio.start_background_task(target=background, exchange=exchange, marketIds=marketIds)


def background(exchange, marketIds):
    marketIdList = tuple(["ws" + exchange + i.replace(" ", "") for i in marketIds.split(",")])

    qs = QuoteServer()
    r = redis.StrictRedis(decode_responses=True)
    p = r.pubsub()
    p.subscribe(*marketIdList)

    for item in p.listen():

        if item['type'] == 'message':
            marketId = item["channel"].replace("ws", "")
            marketId = marketId.replace(exchange, "")
            m = qs.verifyMarketId(marketId)
            if m:
                market = Market(m)
                market.lastPrice = item['data']  # 实时价格
                if market.lastPrice:
                    # 查询能不能直接兑换出该symbol兑法币价格   比如 MT/ETH  KCASH/USDT KCASH/BTC
                    cuPrice = qs.getcuPrice(market.moneyId, currency)
                    # stock coin 是ETH BTC  等大币种
                    if cuPrice:
                        price = qs.calculatePrice(market.lastPrice, cuPrice)

                    else:
                        # 没有直接兑换的 ，需要中间值
                        # KCASH/MT   MT/KCASH
                        # KCASH/MT MT/ETH
                        midId, midPrice = qs.getMidPrice(market.moneyId, market.marketId)
                        cuPrice = qs.getcuPrice(midId, currency)
                        if midPrice and cuPrice:
                            price = qs.calculatePrice(float(market.lastPrice) * midPrice, cuPrice)
                else:
                    # logs.info(f"{market.symbol}在ByteTrade当前报价为0")
                    price = 0

                socketio.emit('server_response',
                              {
                                  'price': price,
                                  'currency': currency,
                                  'exchange': exchange,
                                  'marketId': marketId,
                                  'symbol': market.symbol,
                              }, namespace='/wsPriceServer')
            else:
                logger.info("无效的marketId")


if __name__ == '__main__':
    app.run(host="0.0.0.0", port="5000", debug=False)
