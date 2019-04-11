# coding=utf-8
import base64
import hmac
import copy
import urllib
from urllib import parse

from wssExchange.base.basewss import *
import zlib
import ccxt

# 常量定义
HUOBI_WSS_TRADE = 'wss://api.huobi.pro/ws/v1'  # 交易地址
HUOBI_WSS = 'wss://api.huobi.pro/ws'  # 行情地址
HUOBI_RESTFUL = 'https://api.huobi.pro'


# 获取UTC时间
def _utc():
    return datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S')


# 计算鉴权签名
def _sign(param=None, _accessKeySecret=None):
    # 签名参数:
    # _host = "api.huobipro.com"
    _host = "api.huobi.pro"
    path = "/ws/v1"
    params = {}
    params['SignatureMethod'] = param.get('SignatureMethod') if type(param.get('SignatureMethod')) == type(
        'a') else '' if param.get('SignatureMethod') else ''
    params['SignatureVersion'] = param.get('SignatureVersion') if type(param.get('SignatureVersion')) == type(
        'a') else '' if param.get('SignatureVersion') else ''
    params['AccessKeyId'] = param.get('AccessKeyId') if type(param.get('AccessKeyId')) == type(
        'a') else '' if param.get('AccessKeyId') else ''
    params['Timestamp'] = param.get('Timestamp') if type(param.get('Timestamp')) == type('a') else '' if param.get(
        'Timestamp') else ''
    # 对参数进行排序:
    sortedParams = sorted(params.items(), key=lambda d: d[0], reverse=False)
    # print(sortedParams)

    # 加入&
    qs = urllib.parse.urlencode(sortedParams)
    # 请求方法，域名，路径，参数 后加入`\n`
    payload = ['GET', _host, path, qs]

    payload = '\n'.join(payload)

    dig = hmac.new(_accessKeySecret.encode('utf-8'), msg=payload.encode('utf-8'), digestmod=hashlib.sha256).digest()
    # 进行base64编码
    return base64.b64encode(dig).decode()


########################################################################


class huobiproTemp(BaseWss, ccxt.huobipro):
    def __init__(self, config={}):
        # config.update({'wssUrl': HUOBI_WSS})
        # config.update({'wssUrl': HUOBI_WSS_TRADE})
        BaseWss.__init__(self, config)
        ccxt.huobipro.__init__(self, config)
        self.symbols = {}
        self.id = -1

    def pong(self, data):
        """响应心跳"""
        if "ping" in data:

            req = {'pong': data['ping']}
        else:
            req = {"op": "pong",
                   'ts': data['ts']}
        self.sendJson(req)

    def parseWssbalance(self, response):
        """
        火币wss资产解析
        :param response:
        :return:
        """
        balances = response['list']
        res = []
        if len(balances) > 1:
            # 成交
            for b in balances:
                info = {}
                info["currency"] = b["currency"].upper()
                info["total"] = b["balance"]
                res.append(info)
        else:
            # 没成交
            for b in balances:
                info = {}
                info["currency"] = b["currency"].upper()
                info["free"] = b["balance"]
                res.append(info)
        result = {'info': response}
        result["balance"] = res
        return result

    def onData(self, data):
        if 'ping' in data:
            self.pong(data)
        elif "ping" in data.values():
            self.pong(data)
        elif 'ch' in data:
            symbols = data['ch'].split('.')
            self.load_markets()
            market = self.find_market(symbols[1])
            if 'depth.step' in data['ch']:
                self.callbackDepth(market['symbol'], symbols[3],
                                   self.parse_order_book(data['tick'], timestamp=data['ts']))
            elif 'trade.detail' in data['ch']:
                self.callbackDeals(market['symbol'], self.parse_trades(data['tick']['data'], market))
            elif 'detail' in data['ch']:
                self.callbackTicker(market['symbol'], self.parse_ticker(data['tick'], market))
            elif 'kline' in data['ch']:
                self.callbackKlines(market['symbol'], symbols[3], self.parse_ohlcv(data['tick'], market))
        elif 'op' in data:
            if "topic" in data and "data" in data and "accounts" in data["topic"]:
                self.callbackBalance("", self.parseWssbalance(data["data"]))
            elif 'err-code' in data:
                if data["err-code"] == 0:
                    pass
                else:
                    logErr.error(u'错误代码：%s, 信息：%s' % (data['err-code'], data['err-msg']))

    # ----------------------------------------------------------------------
    def onMessage(self, data):
        """数据推送"""
        try:
            res = zlib.decompress(data, 47).decode('utf-8')
            jdata = json.loads(res)
            self.onData(jdata)
        except zlib.error:
            logErr.error(u'数据解压出错：%s' % jdata)

    def transHuobiSymbol(self, bttSymbol):
        symbolPair = bttSymbol.split('/')
        return symbolPair[0].lower() + symbolPair[1].lower()

    # ----------------------------------------------------------------------
    def subscribeTicker(self, symbol, onTicker):
        """订阅市场细节"""
        self.id += 1
        topic = {
            "sub": 'market.%s.detail' % self.transHuobiSymbol(symbol),
            "id": self.id
        }
        self.subTopic(topic)
        super(huobiproTemp, self).subscribeTicker(symbol, onTicker)

    # ----------------------------------------------------------------------
    def subscribeDepth(self, symbol, onDepth, type='step0'):
        """订阅行情深度"""
        self.id += 1
        topic = {
            "sub": 'market.%s.depth.%s' % (self.transHuobiSymbol(symbol), type),
            "id": self.id
        }
        self.subTopic(topic)
        super(huobiproTemp, self).subscribeDepth(symbol, onDepth, type)

    # ----------------------------------------------------------------------
    def subscribeDeals(self, symbol, onDeals):
        """订阅成交细节"""
        self.id += 1
        topic = {
            "sub": 'market.%s.trade.detail' % self.transHuobiSymbol(symbol),
            "id": self.id
        }
        self.subTopic(topic)
        super(huobiproTemp, self).subscribeDeals(symbol, onDeals)

    # ----------------------------------------------------------------------
    def subscribeKlines(self, symbol, period, onKlines):
        self.id += 1
        topic = {
            "sub": 'market.%s.kline.%s' % (self.transHuobiSymbol(symbol), period),
            "id": self.id
        }
        self.subTopic(topic)
        super(huobiproTemp, self).subscribeKlines(symbol, period, onKlines)

    # ----------------------------------------------------------------------

    def signServer(self):
        """用户鉴权"""
        self.id += 1
        topic = {
            "op": "auth",
            "AccessKeyId": self.apiKey,
            "SignatureMethod": "HmacSHA256",
            "SignatureVersion": "2",
            "Timestamp": _utc(),
        }
        Signature = _sign(topic, self.secret)
        topic["Signature"] = Signature

        self.subTopic(topic)

    # ----------------------------------------------------------------------

    def subscribeOrders(self, symbol, onOrders=None):
        """订阅委托推送"""
        self.signServer()
        time.sleep(1)
        self.id += 1
        topic = {
            "op": "sub",
            "topic": f"orders.{self.transHuobiSymbol(symbol)}",
        }
        self.subTopic(topic)
        super(huobiproTemp, self).subscribeOrders(symbol, onOrders)

    # ----------------------------------------------------------------------
    def subscribeBalance(self, symbol="", onBalance=None, model=None):
        """订阅资金推送"""
        self.signServer()
        time.sleep(1)
        self.id += 1
        topic = {
            "op": "sub",
            "topic": "accounts",
            "model": str(model)
        }
        self.subTopic(topic)
        super(huobiproTemp, self).subscribeBalance(symbol, onBalance)


class huobipro(BaseWss, ccxt.huobipro):
    def __init__(self, config={}):
        BaseWss.__init__(self, config)
        ccxt.huobipro.__init__(self, config)
        if "wssUrl" in config.keys():
            config.pop("wssUrl")
        config["wssUrl"] = HUOBI_WSS_TRADE
        tradeConf = config
        temp = copy.deepcopy(config)
        temp["wssUrl"] = HUOBI_WSS
        marketConf = temp
        secret = config.get("secret", None)
        self.flag = False
        if not secret:
            self.flag = False
        else:
            self.flag = True

        if self.flag:
            self.huobiTrade1 = huobiproTemp(tradeConf)
            self.huobiTrade2 = huobiproTemp(tradeConf)
            self.huobiMarket = huobiproTemp(marketConf)
        else:
            self.huobiMarket = huobiproTemp(marketConf)

    def start(self):
        if self.flag:
            self.huobiTrade1.start()
            self.huobiTrade2.start()
            self.huobiMarket.start()
        else:
            self.huobiMarket.start()

    # ----------------------------------------------------------------------
    def subscribeTicker(self, symbol, onTicker):
        """订阅市场细节"""
        self.huobiMarket.subscribeTicker(symbol, onTicker)

    # ----------------------------------------------------------------------
    def subscribeDepth(self, symbol, onDepth, type='step0'):
        """订阅行情深度"""
        self.huobiMarket.subscribeDepth(symbol, onDepth, type)

    # ----------------------------------------------------------------------
    def subscribeDeals(self, symbol, onDeals):
        """订阅成交细节"""
        self.huobiMarket.subscribeDeals(symbol, onDeals)

    # ----------------------------------------------------------------------
    def subscribeKlines(self, symbol, period, onKlines):
        self.huobiMarket.subscribeKlines(symbol, period, onKlines)

    # ----------------------------------------------------------------------

    def subscribeOrders(self, symbol, onOrders=None):
        """订阅委托推送"""
        if self.flag:
            self.huobiTrade1.subscribeOrders(symbol, onOrders)
        else:
            logErr.error("请输入key and secret")

    # ----------------------------------------------------------------------
    def subscribeBalance(self, symbol="", onBalance=None):
        """订阅资金推送"""
        if self.flag:
            self.huobiTrade1.subscribeBalance(symbol, onBalance, model=0)
            self.huobiTrade2.subscribeBalance(symbol, onBalance, model=1)
        else:
            logErr.error("请输入key and secret")


if __name__ == '__main__':
    def onDepth(symbol=None, data=None):
        print("=" * 100)
        print(symbol, data)
        # print("onDepth", symbol, data)


    def onDeal(symbol, data):
        print("onDeal: ", symbol, data)



    wss1 = huobipro({"apiKey": "24ccad5-a4d915f5-20e78",
                        "secret": "fc32c7a8-8dd1c07b-80c4a",})
    # wss2 = huobiproTemp({"apiKey": "6892475f-308e2f26-163666db-0e387",
    #                     "secret": "7fed2c88-bf6981ff-11a0ef5e-907f4",
    #                     "wssUrl": HUOBI_WSS_TRADE})

    # wss = huobipro()
    # b = wss.fetch_markets()
    # for i in b:
    #     print(i['symbol'],i['precision'])
    # wss.start()
    # wss.subscribeTicker('BTC/USDT',onDepth)
    wss1.start()
    wss1.subscribeBalance(onBalance=onDepth)
    # wss2.start()
    # wss1.signServer()
    # wss1.subscribeBalance(model=1)
    # wss1.subscribeBalance(model=0)
    # wss2.subscribeBalance(model=1)
    # wss.subscribeBalance()
    # wss.subscribeOrders("MT/ETH")
    # wss.subscribeDeals('BTC/USDT', onDeal)
    # wss.subscribeDepth('MT/ETH', onDepth)
    # wss.subscribeDeals('BAT/ETH',onDepth)
    # wss.subscribeTicker('BAT/ETH',onDepth)
    # wss.subscribeDeals('CMT/ETH',onDepth)
    # wss.subscribeTicker('CMT/ETH',onDepth)
    # wss.subscribeDeals('ZRX/ETH',onDepth)
    # wss.subscribeTicker('ZRX/ETH',onDepth)
    # wss.subscribeKlines('BTC/USDT','1min', onDepth)
    # wss.fetch_ohlcv('BTC/USDT')
    # print(wss.has.get('fetchTickers') or wss.has.get('fetch_tickers'))
    # print(wss.fetch_tickers())
    # print(wss.subscribeTicker('BTC/USDT', onDepth))
