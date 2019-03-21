# coding=utf-8
from wssExchange.base.basesub import *
from wssExchange.base.basewss import *
import ccxt
import types

# 常量定义
BINANCE_WSS = 'wss://stream.binance.com:9443/ws/'

G_BINANCE = ccxt.binance()

def parseWssOhlcv(ohlcv,market=None,timeframe='1m',since=None,limit=None):
    return [
        ohlcv['t'],
        ohlcv['o'],
        ohlcv['h'],
        ohlcv['l'],
        ohlcv['c'],
        ohlcv['v'],
    ]

def parseWssTrade(trade,market=None):
    timestampField='T' if ('T' in list(trade.keys())) else 'time'
    timestamp=G_BINANCE.safe_integer(trade,timestampField)
    priceField='p' if ('p' in list(trade.keys())) else 'price'
    price=G_BINANCE.safe_float(trade,priceField)
    amountField='q' if ('q' in list(trade.keys())) else 'qty'
    amount=G_BINANCE.safe_float(trade,amountField)
    idField='a' if ('a' in list(trade.keys())) else 'id'
    id=G_BINANCE.safe_string(trade,idField)
    order=G_BINANCE.safe_string(trade,'orderId')
    side='sell' if trade['m'] else 'buy'  # self is reversed intentionally
    return {
        'info':trade,
        'timestamp':timestamp,
        'datetime':G_BINANCE.iso8601(timestamp),
        'symbol':market['symbol'],
        'id':id,
        'order':order,
        'type':None,
        'takerOrMaker':None,
        'side':side,
        'price':price,
        'cost':price*amount,
        'amount':amount,
        'fee':None,
    }

def parseWssTicker(ticker,market=None):
    timestamp=G_BINANCE.safe_integer(ticker,'E')
    last=G_BINANCE.safe_float(ticker,'c')
    return {
        'symbol':market['symbol'],
        'timestamp':timestamp,
        'datetime':G_BINANCE.iso8601(timestamp),
        'high':G_BINANCE.safe_float(ticker,'h'),
        'low':G_BINANCE.safe_float(ticker,'l'),
        'bid':G_BINANCE.safe_float(ticker,'b'),
        'bidVolume':G_BINANCE.safe_float(ticker,'B'),
        'ask':G_BINANCE.safe_float(ticker,'a'),
        'askVolume':G_BINANCE.safe_float(ticker,'A'),
        'vwap':G_BINANCE.safe_float(ticker,'w'),
        'open':G_BINANCE.safe_float(ticker,'o'),
        'close':last,
        'last':last,
        'previousClose':G_BINANCE.safe_float(ticker,'x'),
        'change':G_BINANCE.safe_float(ticker,'p'),
        'percentage':G_BINANCE.safe_float(ticker,'P'),
        'average':None,
        'baseVolume':G_BINANCE.safe_float(ticker,'v'),
        'quoteVolume':G_BINANCE.safe_float(ticker,'q'),
        'info':ticker,}

def onMessage(self,data):
    if not data:
        return
    jdata=json.loads(data)
    topic=self.wssUrl.split('/')[-1]#jdata['s']
    symbol,name=topic.split('@')
    G_BINANCE.load_markets()
    market=G_BINANCE.find_market(symbol.upper())
    bttSymbol = G_BINANCE.find_symbol(symbol,market)
    if 'lastUpdateId' in jdata:
        self.callbackDepth(bttSymbol,name.replace('depth',''),G_BINANCE.parse_order_book(jdata))
    elif 'trade'==jdata['e']:
        self.callbackDeals(bttSymbol,[parseWssTrade(jdata, market)])
    elif '24hrTicker'==jdata['e']:
        self.callbackTicker(bttSymbol,parseWssTicker(jdata,market))
    elif 'kline'==jdata['e']:
        self.callbackKlines(bttSymbol,jdata['k']['i'],parseWssOhlcv(jdata['k'],market))
    else:
        logErr.error('-'*50)
        logErr.error(data)
        logErr.error('-'*50)

def onHeartBeat(self):
    pass
    # self.sendRequest('pong')

########################################################################
class binance(BaseSub,ccxt.binance):
    def __init__(self, config={}):
        config.update({'wssUrl': BINANCE_WSS})
        BaseSub.__init__(self)
        ccxt.binance.__init__(self, config)
        self.symbols = {}
        self.wssList = {}

    def start(self):
        pass

    # ----------------------------------------------------------------------
    def newWssTopic(self, topic):
        """订阅主题"""
        if topic in self.wssList:
            return
        wss = BaseWss()
        wss.onMessage = types.MethodType(onMessage,wss)
        wss.onHeartBeat = types.MethodType(onHeartBeat,wss)
        wss.init('%s%s'%(BINANCE_WSS,topic))
        wss.start()
        self.wssList[topic]=wss
        return wss

    def toBinanceSymbol(self, bttSymbol):
        symbolPair = bttSymbol.split('/')
        return symbolPair[0].lower() + symbolPair[1].lower()

    # ----------------------------------------------------------------------
    def subscribeTicker(self, symbol, onTicker):
        """订阅市场细节"""
        topic = self.toBinanceSymbol(symbol) + '@ticker'
        wss = self.newWssTopic(topic)
        wss.subscribeTicker(symbol, onTicker)

    # ----------------------------------------------------------------------
    def subscribeDepth(self, symbol, onDepth, type='20'):
        """订阅行情深度"""
        topic = self.toBinanceSymbol(symbol) + '@depth' + type
        wss=self.newWssTopic(topic)
        wss.subscribeDepth(symbol, onDepth, type)

    # ----------------------------------------------------------------------
    def subscribeDeals(self, symbol, onDeals):
        """订阅成交细节"""
        topic = self.toBinanceSymbol(symbol)+'@trade'
        wss=self.newWssTopic(topic)
        wss.subscribeDeals(symbol, onDeals)

    # ----------------------------------------------------------------------
    def subscribeKlines(self, symbol, period, onKlines):
        topic = self.toBinanceSymbol(symbol) + '@kline_' + period
        wss=self.newWssTopic(topic)
        wss.subscribeKlines(symbol, period, onKlines)

    # ----------------------------------------------------------------------
    def subscribeOrders(self, symbol, onOrders):
        """订阅委托推送"""
        raise NotImplementedError('Not Implemented')

    # ----------------------------------------------------------------------
    def subscribeBalance(self, symbol, onBalance):
        """订阅资金推送"""
        raise NotImplementedError('Not Implemented')


if __name__ == '__main__':
    def onDepth(symbol, data):
        print("", symbol, data)

    wss = binance()
    print(wss.has)
    wss.start()
    # wss.subscribeTicker('BTC/USDT', onDepth)
    # wss.subscribeDepth('BTC/USDT', onDepth)
    wss.subscribeDeals('BTC/USDT',onDepth)
    # wss.subscribeKlines('BTC/USDT','1m', onDepth)
    while True:
        pass
    # print(wss.fetch_tickers())
    # print(wss.fetchTicker('BTC/USDT'))
