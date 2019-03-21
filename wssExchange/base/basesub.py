# encoding: UTF-8
import hashlib
import json

class BaseSub(object):
    def __init__(self):
        """Constructor"""
        self.subDict = {}
        self.cbFuntions = {}

    # ----------------------------------------------------------------------
    def start(self):
        raise NotImplementedError('Not implemented start')

    # ----------------------------------------------------------------------
    def resubscribe(self):
        """重新订阅"""
        d = self.subDict
        self.subDict = {}
        for i in d:
            self.subTopic(d[i])

    # ----------------------------------------------------------------------
    def subTopic(self, topic):
        """订阅主题"""
        id = hashlib.sha1(json.dumps(topic).encode('utf-8')).hexdigest()
        if id in self.subDict:
            return
        self.subDict[id] = topic

    def addCallback(self, symbol, onCallback):
        if symbol not in self.cbFuntions:
            self.cbFuntions[symbol] = []
        if onCallback not in self.cbFuntions[symbol]:
            self.cbFuntions[symbol].append(onCallback)

    def callback(self, symbol, type, params):
        cbSymbol = type + ':' + symbol
        # symbol marketid
        if cbSymbol in self.cbFuntions:
            for cb in self.cbFuntions[cbSymbol]:
                cb(symbol, params)

    def subscribeDepth(self, symbol, onDepth, type):
        typeSymbol = '' if not type else type
        self.addCallback(f'Depth{typeSymbol}:{symbol}', onDepth)

    def callbackDepth(self, symbol, type, data):
        depthType = 'Depth'
        if type:
            depthType = 'Depth' + type
        self.callback(symbol,depthType,data)

    def subscribeTicker(self, symbol, onTicker):
        self.addCallback('Ticker:' + symbol, onTicker)

    def callbackTicker(self, symbol, data):
        self.callback(symbol, 'Ticker', data)

    def subscribeOrders(self, symbol, onOrders):
        self.addCallback('Orders:' + symbol, onOrders)

    def callbackOrders(self, symbol, data):
        self.callback(symbol, 'Orders', data)

    def subscribeBalance(self, symbol, onBalance):
        self.addCallback('Balance:' + str(symbol), onBalance)

    def callbackBalance(self, symbol, data):
        self.callback(symbol, 'Balance', data)

    def subscribeKlines(self, symbol, period, onKlines):
        self.addCallback('Klines:%s:%s' % (period, symbol), onKlines)

    def callbackKlines(self, symbol, period, data):
        self.callback(symbol, 'Klines:' + period, data)

    def subscribeDeals(self, symbol, onDeals):
        self.addCallback('Deals:' + symbol, onDeals)

    def callbackDeals(self, symbol, data):
        self.callback(symbol, 'Deals', data)
