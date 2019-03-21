#coding=utf-8
from wssExchange.base.basesub import BaseSub
import wssExchange
import ccxt
# 常量定义
import logging
log = logging.getLogger()
import time
from threading import Thread

def simwss(exName, config={}):
    if exName in dir(wssExchange):
        exClass = getattr(wssExchange,exName)
    else:
        exClass = getattr(ccxt,exName)
    class Timer(BaseSub,exClass):
        # ----------------------------------------------------------------------
        def __init__(self, config={}):
            """Constructor"""
            self.timerThread = None
            self.subFunction = []
            self.active = False
            self.wait = config.get('wait') if config.get('wait') else 60
            super(Timer, self).__init__()
            super(BaseSub, self).__init__(config)
        # ----------------------------------------------------------------------
        def start(self):
            self.load_markets()
            if not self.timerThread:
                self.active = True
                self.timerThread = Thread(target=self.timer)
                self.timerThread.start()
        # ----------------------------------------------------------------------
        def close(self):
            """停止"""
            if self.active:
                self.active = False
                self.timerThread.join()
        # ----------------------------------------------------------------------
        def timer(self):
            while self.active==True:
                for subFun in self.subFunction:
                    try:
                        data = subFun['call'](*subFun['param'])
                        if data:
                            cbFun = subFun['callback']
                            param = subFun['param']+[data]
                            cbFun(*param)
                    except Exception as e:
                        log.error('error in timer as %s'%e)
                time.sleep(60)
        # ----------------------------------------------------------------------
        def subscribeDepth(self, symbol, onDepth, type=None):
            if self.has.get('fetch_order_book') or self.has.get('fetchOrderBook'):
                self.subFunction.append({
                    'call'      :self.fetch_order_book,
                    'callback'  :self.callbackDepth,
                    'param'     :[symbol,type]
                })
            else:
                raise NotImplementedError('no fetch_open_orders implement in %s!'%self.id)
            super(Timer,self).subscribeDepth(symbol, onDepth, type)
        # ----------------------------------------------------------------------
        def subscribeTicker(self, symbol, onTicker):
            if self.has.get('fetch_ticker') or self.has.get('fetchTicker'):
                self.subFunction.append({
                    'call'      :self.fetch_ticker,
                    'callback'  :self.callbackTicker,
                    'param'     :[symbol]
                })
            else:
                raise NotImplementedError('no fetch_ticker implement in %s!'%self.id)
            super(Timer,self).subscribeTicker(symbol, onTicker)
        # ----------------------------------------------------------------------
        def subscribeOrders(self, symbol, onOrders):
            if self.has('fetch_open_orders') or self.has('fetchOpenOrders'):
                self.subFunction.append({
                    'call'      :self.fetch_open_orders,
                    'callback'  :self.callbackOrders,
                    'param'     :[symbol]
                })
            else:
                raise NotImplementedError('no fetch_open_orders implement in %s!'%self.id)
            super(Timer,self).subscribeOrders(symbol, onOrders)
        # ----------------------------------------------------------------------
        def subscribeBalance(self, symbol, onBalance):
            if self.has.get('fetch_balance') or self.has.get('fetchBalance'):
                self.subFunction.append({
                    'call'      :self.fetch_balance,
                    'callback'  :self.callbackBalance,
                    'param'     :[symbol]
                })
            else:
                raise NotImplementedError('no fetch_balance implement in %s!'%self.id)
            super(Timer,self).subscribeBalance(symbol, onBalance)
        # ----------------------------------------------------------------------
        def subscribeKlines(self, symbol, period, onKlines):
            if self.has.get('fetch_ohlcv') or self.has.get('fetchOHLCV'):
                self.subFunction.append({
                    'call'      :self.fetch_ohlcv,
                    'callback'  :self.callbackKlines,
                    'param'     :[symbol,period]
                })
            else:
                raise NotImplementedError('no fetch_ohlcv implement in %s!'%self.id)
            super(Timer,self).subscribeKlines(symbol, period, onKlines)
        # ----------------------------------------------------------------------
        def subscribeDeals(self, symbol, onDeals):
            if self.has.get('fetch_trades') or self.has.get('fetchTrades'):
                self.subFunction.append({
                    'call'      :self.fetch_trades,
                    'callback'  :self.callbackDeals,
                    'param'     :[symbol]
                })
            else:
                raise NotImplementedError('no fetch_open_orders implement %s!'%self.id)
            super(Timer,self).subscribeDeals(symbol, onDeals)
    return Timer(config)

if __name__ == '__main__':
    def onTicker(symbol, data):
        print(symbol, data)
    f = simwss('btcturk')
    f.userAgent = 'Mozilla/5.0'
    f.start()
    f.subscribeTicker('USD/TTR', onTicker)

