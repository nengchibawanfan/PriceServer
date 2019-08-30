# coding=utf-8
from wssExchange.base.basewss import *
from bytetradeLib.ccxtBytetrade import ccxtBytetrade
import arrow

TEST = False
# 常量定义
# BYTETRADE_WSS = 'wss://p2.bytetrade.io/ws/'
# BYTETRADE_API = 'http://p2.bytetrade.io/bittrade/v1/me'
# BYTETRADE_WSS = 'ws://13.56.53.82:8008/ws/'
# BYTETRADE_API = 'http://13.56.53.82:6081/bittrade/v1/me'
# BYTETRADE_WSS = 'ws://54.67.14.158:8008/'
# BYTETRADE_API = 'http://54.67.14.158:6081/bittrade/v1/me'
if TEST:
    BYTETRADE_WSS = 'wss://c2.bytetrade.io/ws/'
    BYTETRADE_API = 'https://c2.bytetrade.io/bittrade/v1/me'
else:
    BYTETRADE_WSS = 'wss://p2.bytetrade.com/ws/'
    BYTETRADE_API = 'https://p2.bytetrade.com/bittrade/v1/me'


########################################################################
class bytetrade(BaseWss, ccxtBytetrade):
    def __init__(self, config={}):
        config.update({'apiUrl': BYTETRADE_API})
        ccxtBytetrade.__init__(self, config)
        BaseWss.__init__(self, config)
        self.subId = 0
        self.depthData = {}
        self.wssUrl = BYTETRADE_WSS

    def onHeartBeat(self):
        """响应心跳"""
        req = {'id': 0, 'method': 'server.ping', 'params': []}
        if self._getWs():
            self.sendJson(req)

    def parseWssDeal(self, symbol, deal):
        now = arrow.get(int(deal['time']))
        return {
            'info': deal,
            'timestamp': now.timestamp,
            'datetime': '%s' % now,
            'symbol': symbol,
            'id': deal['id'],
            'order': None,
            'type': None,
            'side': deal['type'],
            'price': float(deal['price']),
            'amount': float(deal['amount']),
        }

    def parseWssTicker(self, ticker, symbol):
        last = self.safe_float(ticker, 'last')
        now = arrow.now()
        return {
            'symbol': symbol,
            'timestamp': now.timestamp,
            'datetime': str(now),
            'high': self.safe_float(ticker, 'high'),
            'low': self.safe_float(ticker, 'low'),
            'bid': last,
            'bidVolume': None,
            'ask': last,
            'askVolume': None,
            'vwap': None,
            'open': self.safe_float(ticker, 'open'),
            'close': last,
            'last': last,
            'previousClose': None,
            'change': None,
            'percentage': None,
            'average': None,
            'baseVolume': self.safe_float(ticker, 'volume'),
            'quoteVolume': None,
            'info': ticker,
        }

    def parseDepthData(self, depthData, symbol):
        if symbol not in self.depthData:
            self.depthData[symbol]={'asks':[],'bids':[]}
        self.depthData[symbol] = self.replaceDepthNew(self.depthData[symbol], depthData[1], depthData[0])
        self.depthData[symbol]['timestamp'] = arrow.now().timestamp
        return self.depthData[symbol]

    def parseBTTOrderStatus(self, status):
        # 1 open   3 deal/cancel
        parsed = ''
        if status == 1:
            parsed = 'open'
        elif status == 2:
            parsed = 'open'
        elif status == 3:
            parsed = 'closed'
        return parsed

    def calcMarketId(self, symbol):
        symbolPair = symbol.split('/')
        return int(symbolPair[1]) * 2147483647 + int(symbolPair[0])

    def calcSymbol(self, marketId):
        marketId = int(marketId)
        return int(marketId % 2147483647), int(marketId / 2147483647)

    def parseWssBalance(self, balance):
        ret = {}
        if balance:
            # ret["exchange_name"] = "bytetrade"
            ret['free'] = float(list(balance.values())[0][0])
            ret['used'] = float(list(balance.values())[0][1])
            total = ret['free'] + ret['used']
            ret['total'] = total
            ret['id'] = str(list(balance.keys())[0])
            if self.assets:
                if self.calcAmountString(ret['free'], ret['id']) == '0': ret['free'] = 0
                if self.calcAmountString(ret['used'], ret['id']) == '0': ret['used'] = 0
                total = ret['free'] + ret['used']
                if self.calcAmountString(total, ret['id']) == '0': ret['total'] = 0
        return ret

    def parseWssOrder(self, order, status):
        remaining = float(order['left'])
        amount = float(order['amount'])
        filled = amount - remaining
        cOrder = {
            'info': order,
            'id': str(order['id']),
            'timestamp': str(arrow.get(order['ctime'])),
            'datetime': str(arrow.get(order['ctime'])),
            'lastTradeTimestamp': str(arrow.get(order['mtime'])),
            'symbol': order['market_id'],
            'pair': order['market'],    # CMT/ETH
            'type': 'limit' if order['type'] == 1 else 'market',
            'side': 'sell' if order['side'] == 1 else 'buy',
            'price': float(order['price']),
            'average': 0,
            'cost': float(order['deal_money']),
            'amount': amount,
            'filled': filled,
            'remaining': remaining,
            'status': self.parseBTTOrderStatus(status),
            'fee': float(order['deal_fee']),
            'bttFee': float(order.get('freezeBttFee', 0)),
            "exchange_name": "bytetrade",
        }
        return cOrder

    def onMessage(self, data):
        """数据推送"""
        try:
            jdata = json.loads(data)
            if 'params' in jdata:
                if 'depth' in jdata['method']:
                    marketId = jdata['params'][2]
                    symbolPair = self.calcSymbol(marketId)
                    bttSymbol=f'{symbolPair[0]}/{symbolPair[1]}'
                    self.callbackDepth(bttSymbol, None, self.parseDepthData(jdata['params'], bttSymbol))
                elif 'deals' in jdata['method']:
                    marketId = jdata['params'][0]
                    symbolPair=self.calcSymbol(marketId)
                    bttSymbol = f'{symbolPair[0]}/{symbolPair[1]}'
                    self.callbackDeals(bttSymbol,[self.parseWssDeal(bttSymbol, deal) for deal in jdata['params'][1]])
                elif 'today' in jdata['method']:
                    marketId = jdata['params'][0]
                    symbolPair=self.calcSymbol(marketId)
                    bttSymbol=f'{symbolPair[0]}/{symbolPair[1]}'
                    self.callbackTicker(bttSymbol, self.parseWssTicker(jdata['params'][1], bttSymbol))
                elif 'order' in jdata['method']:
                    marketId = jdata['params'][1]['market_id']
                    symbolPair=self.calcSymbol(marketId)
                    bttSymbol=f'{symbolPair[0]}/{symbolPair[1]}'
                    order = self.parseWssOrder(jdata['params'][1], jdata['params'][0])
                    self.callbackOrders(bttSymbol, order)
                elif 'asset' in jdata['method']:
                    asset = jdata['params'][0]
                    balance = self.parseWssBalance(asset)
                    self.callbackBalance(list(asset.keys())[0], balance)
            elif 'error' in jdata and jdata['error'] != None:
                logErr.error(u'错误代码：%s, 信息：%s' % (jdata['error'], jdata['result']))
            else:
                print(jdata)
        except Exception as e:
            logErr.error('%s wss onMessage Exception: %s, %s' % (self.subId, e, data))

    # ----------------------------------------------------------------------
    def subscribeTicker(self, symbol, onTicker):
        """订阅市场细节"""
        reqSymbol = symbol if isinstance(symbol, list) else [symbol]
        marketIds = [self.calcMarketId(s) for s in reqSymbol]
        self.subId += 1
        topic = {
            "id": self.subId,
            "method": 'today.subscribe',
            "params": marketIds,
        }
        self.subTopic(topic)
        for r in reqSymbol:
            super(bytetrade, self).subscribeTicker(r, onTicker)

    # ----------------------------------------------------------------------
    def subscribeDepth(self, symbol, onDepth, type=100):
        """订阅行情深度"""
        reqSymbol = symbol if isinstance(symbol,list) else [symbol]
        for r in reqSymbol:
            self.subId += 1
            marketId = str(self.calcMarketId(r))
            topic = {
                "id": self.subId,
                "method": 'depth.subscribe',
                "params": [marketId, type, '0.0000000001'],
            }
            self.subTopic(topic)
            super(bytetrade, self).subscribeDepth(r, onDepth, None)

    # ----------------------------------------------------------------------
    def subscribeDeals(self, symbol, onDeals):
        """订阅成交细节"""
        self.subId += 1
        reqSymbol=symbol if isinstance(symbol,list) else [symbol]
        marketIds=[self.calcMarketId(s) for s in reqSymbol]
        topic = {
            "id": self.subId,
            "method": 'deals.subscribe',
            "params": marketIds,
        }
        self.subTopic(topic)
        for r in reqSymbol:
            super(bytetrade, self).subscribeDeals(r, onDeals)

    # ----------------------------------------------------------------------
    def subscribeKlines(self, symbol, period, onKlines):
        """
        self.subId+=1
        topic = {
            "id": self.subId,
            "method": 'kline.subscribe',
            "params": [symbol, 1]
        }
        self.subTopic(topic)
        super(bytetrade,self).subscribeBalance(symbol, onKlines)
        """
        raise NotImplementedError('Not Implemented')

    def signServer(self):
        """用户鉴权"""
        self.subId += 1
        topic = {
            "id": self.subId,
            "method": 'server.sign',
            "params": [self.apiKey],
        }
        self.subTopic(topic)

    # ----------------------------------------------------------------------
    def subscribeOrders(self, symbol, onOrders):
        # """订阅委托推送"""
        self.signServer()
        reqSymbol=symbol if isinstance(symbol,list) else [symbol]
        marketIds=[str(self.calcMarketId(s)) for s in reqSymbol]
        self.subId += 1
        topic = {
            "id": self.subId,
            "method": 'order.subscribe',
            "params": marketIds,
        }
        self.subTopic(topic)
        for r in reqSymbol:
            super(bytetrade, self).subscribeOrders(r, onOrders)

    # ----------------------------------------------------------------------
    def subscribeBalance(self, symbol, onBalance):
        """订阅资金推送"""
        self.signServer()
        self.subId += 1
        reqSymbol = symbol if isinstance(symbol, list) else [symbol]
        topic = {
            "id": self.subId,
            "method": 'asset.subscribe2',
            "params": reqSymbol,
        }
        self.subTopic(topic)
        for r in reqSymbol:
            super(bytetrade, self).subscribeBalance(r, onBalance)

    def __mysort(self, a, b, sort_type):
        if (sort_type == 0):
            return float(a) < float(b)
        else:
            return float(a) > float(b)

    def __merge(self, _data, data, isclear, sort_type):
        if (_data == None):
            _data = []
        bids = []
        nbids = []
        for i in range(0, len(data)):
            nbids.append([float(data[i][0]), float(data[i][1])])
            for i in range(0, len(nbids)):
                for j in range(i + 1, len(nbids)):
                    if self.__mysort(nbids[i][0], nbids[j][0], sort_type):
                        t = nbids[i]
                        nbids[i] = float(nbids[j])
                        nbids[j] = float(t)
        if isclear:
            for i in range(0, len(nbids)):
                if nbids[i][1] > 0:
                    bids.append(nbids[i])
        else:
            i = 0
            j = 0
            while i < len(nbids) and j < len(_data):
                if (nbids[i][0] == _data[j][0]):
                    if nbids[i][1] > 0:
                        bids.append(nbids[i])
                    i += 1
                    j += 1
                elif self.__mysort(nbids[i][0], _data[j][0], sort_type):
                    if _data[j][1] > 0:
                        bids.append(_data[j])
                    j += 1
                else:
                    if (nbids[i][1] > 0):
                        bids.append(nbids[i])
                    i += 1
            while i < len(nbids):
                if nbids[i][1] > 0:
                    bids.append(nbids[i])
                i += 1
            while j < len(_data):
                if _data[j][1] > 0:
                    bids.append(_data[j])
                j += 1
        return bids

    def replaceDepthNew(self, newDepth, oldDepth, isclear):
        obj = {}
        if 'bids' in oldDepth:
            bids = self.__merge(newDepth['bids'], oldDepth['bids'], isclear, 0)
            obj['bids'] = bids
        elif 'bids' in newDepth and not isclear:
            obj['bids'] = newDepth['bids']
        if 'asks' in oldDepth:
            asks = self.__merge(newDepth['asks'], oldDepth['asks'], isclear, 1)
            obj['asks'] = asks
        elif 'asks' in newDepth and not isclear:
            obj['asks'] = newDepth['asks']
        return obj


if __name__ == '__main__':
    def onDepth(symbol, data):
        # print("depth: ", symbol, data)
        # print(f"wssdepth {data['timestamp']}", data['bids'][0], data['asks'][0])
        # orderbook = wss.fetch_order_book(symbol)
        # print(f"apidepth {orderbook['timestamp']}", orderbook['bids'][0], orderbook['asks'][0])
        # for i in range(0,len(orderbook['asks'])):
        #     if orderbook['asks'][i]!=data['asks'][i]:
        #         print(f'asks error: index{i} {orderbook["asks"][i]} {arrow.get(orderbook["timestamp"])} {data["asks"][i]} {arrow.get(data["timestamp"])}')
        # for i in range(0,len(orderbook['bids'])):
        #     if orderbook['bids'][i]!=data['bids'][i]:
        #         print(f'bids error: index{i} {orderbook["bids"][i]} {arrow.get(orderbook["timestamp"])} {data["bids"][i]} {arrow.get(data["timestamp"])}')
        # time.sleep(10)
        print("depth: ", symbol, data)

    def onTicker(symbol, data):
        print("ticker: ",symbol,data)
    wss = bytetrade({
        'apiKey': 'heybrit',
        'secret': '',
    })
    # orders = wss.fetch_open_orders('3/2')
    # for o in orders:
    #     wss.cancel_order(o['id'],o['symbol'])
    # for i in range(0,60):
    #     wss.create_order('3/2','limit','buy',10000,0.0001)
    #     time.sleep(5)
    wss.start()
    # wss.subscribeBalance([i for i in range(0,50)], onDepth)
    # wss.subscribeOrders('18/2',onTicker)
    # while True:
    #     pass
    # print(wss.fetch_order_book('BTC/LRT'))
    # wss.subscribeBalance(1,onDepth)
    # while True:
    #    pass
    # print(wss.fetch_balance())
    # print(wss.fetch_balance({'symbol':'LRT'}))
    # wss.subscribeDeals('34/2', onDepth)
    wss.subscribeDeals('3/2', onTicker)
    # wss.subscribeDeals('3/2',onDepth)
    # wss.subscribeOrders('3/2', onDepth)
    # wss.subscribeBalance([1, 3], onDepth)
    # orders=wss.fetch_orders()
    # wss.fetch_order('fadsfsafd','KCASH/ETH')
    # wss.()
    # ret = wss.create_order('KCASH/ETH','limit','sell',10, 0.0009)
    # print(ret)
    # print(wss.fetch_balance())
    # for order in orders:
    #    print(wss.cancel_order(order['id'],'KCASH/ETH'))
