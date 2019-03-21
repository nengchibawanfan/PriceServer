#coding=utf-8
from wssExchange.base.basewss import *
import ccxt
# 常量定义
OKEX_SPOT_HOST = 'wss://real.okex.com:10441/websocket'
import logging
log = logging.getLogger()
import arrow
import zlib
########################################################################

class okex(BaseWss,ccxt.okex):
    def __init__(self, config={}):
        config.update({'wssUrl': OKEX_SPOT_HOST})
        BaseWss.__init__(self,config)
        ccxt.okex.__init__(self,config)
        self.logined = False

    def inflate(self, data):
        decompress = zlib.decompressobj(
            -zlib.MAX_WBITS  # see above
        )
        inflated = decompress.decompress(data)
        inflated += decompress.flush()
        return inflated

    def onMessage(self, data):
        """数据推送"""
        try:
            jdata = json.loads(self.inflate(data))
            self.load_markets()
            for result in jdata:
                if 'data' in result:
                    channel = result['channel']
                    if not channel or channel=='addChannel':
                        return
                    if 'result' not in result['data']:
                        symbols = channel.split('_')
                        bttSymbol = symbols[3].upper() + '/' + symbols[4].upper()
                        if 'ticker' in symbols:
                            self.callbackTicker(bttSymbol, self.parse_ticker(result['data'],self.market(bttSymbol)))
                        elif 'depth' in symbols:
                            self.callbackDepth(bttSymbol, symbols[6], self.parse_order_book(result['data'],timestamp=result['data']['timestamp']))
                        elif 'deals' in symbols:
                            self.callbackDeals(bttSymbol, [self.parse_wss_deal(bttSymbol, deal) for deal in result['data']])
                        elif 'order' in symbols:
                            self.callbackOrders(bttSymbol, self.parse_wss_order(result['data']))
                        #elif 'balance' in symbols:
                        #    self.callbackBalance(bttSymbol, self.parse_balance(result['data']))
                    elif result['data']['result'] == False:
                        log.error('recv okex data error: %s, data %s'%(result['data']['error_code'], result['data']))
        except Exception as e:
            logErr.error('%s wss onMessage Exception: %s, %s, %s'%(self.id,symbols,e,data))

    #----------------------------------------------------------------------
    def onHeartBeat(self):
        """响应心跳"""
        req = {'event': 'ping'}
        self.sendJson(req)

    def transOkSymbol(self, bttSymbol):
        symbolPair = bttSymbol.split('/')
        return symbolPair[0].lower()+'_'+symbolPair[1].lower()

    def parse_wss_deal(self, symbol, deal):
        ts = arrow.get('%s %s'%(arrow.now().date(), deal[3]))
        return {
            'info': deal,
            'timestamp': ts.timestamp,
            'datetime': '%s'%ts,
            'symbol': symbol,
            'id': str(deal[0]),
            'order': None,
            'type': None,
            'side': 'buy' if deal[4]=='ask' else 'sell',
            'price': float(deal[1]),
            'amount': float(deal[2]),
        }

    def parse_order_status(self, status):
        if status == -1:
            return 'canceled'
        if status == 0:
            return 'open'
        if status == 1:
            return 'open'
        if status == 2:
            return 'closed'
        if status == 3:
            return 'open'
        if status == 4:
            return 'canceled'
        return status

    def parse_order_side(self, side):
        if side == 1:
            return 'buy'  # open long position
        if side == 2:
            return 'sell'  # open short position
        if side == 3:
            return 'sell'  # liquidate long position
        if side == 4:
            return 'buy'  # liquidate short position
        return side

    def parse_wss_order(self, order, market=None):
        side = None
        type = None
        if 'tradeType' in order:
            if (order['tradeType'] == 'buy') or (order['tradeType'] == 'sell'):
                side = order['tradeType']
                type = 'limit'
            elif order['tradeType'] == 'buy_market':
                side = 'buy'
                type = 'market'
            elif order['tradeType'] == 'sell_market':
                side = 'sell'
                type = 'market'
            else:
                side = self.parse_order_side(order['tradeType'])
                if ('contract_name' in list(order.keys())) or ('lever_rate' in list(order.keys())):
                    type = 'margin'
        status = self.parse_order_status(order['status'])
        symbol = None
        if market is None:
            marketId = self.safe_string(order, 'symbol')
            if marketId in self.markets_by_id:
                market = self.markets_by_id[marketId]
        if market:
            symbol = market['symbol']
        timestamp = None
        createDateField = self.get_create_date_field()
        if createDateField in order:
            timestamp = order[createDateField]
        amount = self.safe_float(order, 'tradeAmount')
        filled = self.safe_float(order, 'completedTradeAmount')
        amount = max(amount, filled)
        remaining = max(0, amount - filled)
        if type == 'market':
            remaining = 0
        average = self.safe_float(order, 'averagePrice')
        # https://github.com/ccxt/ccxt/issues/2452
        average = self.safe_float(order, 'priceAverage', average)
        cost = average * filled
        result = {
            'info': order,
            'id': str(order['orderId']),
            'timestamp': timestamp,
            'datetime': timestamp,
            'lastTradeTimestamp': None,
            'symbol': symbol,
            'type': type,
            'side': side,
            'price': order['tradePrice'],
            'average': average,
            'cost': cost,
            'amount': amount,
            'filled': filled,
            'remaining': remaining,
            'status': status,
            'fee': None,
        }
        return result

    #----------------------------------------------------------------------
    def generateSign(self, params):
        """生成签名"""
        l = []
        for key in sorted(params.keys()):
            l.append('%s=%s' %(key, params[key]))
        l.append('secret_key=%s' %self.secret)
        sign = '&'.join(l)
        return hashlib.md5(sign.encode('utf-8')).hexdigest().upper()

    def __sendRequest(self, channel, params=None):
        """发送请求"""
        d = {}
        d['event'] = 'addChannel'
        d['channel'] = channel
        # 如果有参数，在参数字典中加上api_key和签名字段
        if params is not None:
            params['api_key'] = self.apiKey
            params['sign'] = self.generateSign(params)
            d['parameters'] = params
        self.subTopic(d)

    def login(self):
        params = {}
        params['api_key'] = self.apiKey
        params['sign'] = self.generateSign(params)
        self.subTopic({"event":"login","parameters":params})
        self.logined=True

    # ----------------------------------------------------------------------
    def subscribeTicker(self, symbol, onTicker):
        """订阅现货的Tick"""
        channel = 'ok_sub_spot_%s_ticker' % self.transOkSymbol(symbol)
        self.subTopic({'event':'addChannel','channel':channel})
        super(okex,self).subscribeTicker(symbol, onTicker)

    # ----------------------------------------------------------------------
    def subscribeDepth(self, symbol, onDepth, type=20):
        """订阅现货的深度"""
        channel = 'ok_sub_spot_%s_depth' % self.transOkSymbol(symbol)
        if type:
            channel = channel + '_' + str(type)
        self.subTopic({'event':'addChannel','channel':channel})
        super(okex,self).subscribeDepth(symbol, onDepth, str(type))

    # ----------------------------------------------------------------------
    def subscribeDeals(self, symbol, onDeals):
        channel = 'ok_sub_spot_%s_deals' % self.transOkSymbol(symbol)
        self.subTopic({'event':'addChannel','channel':channel})
        super(okex,self).subscribeDeals(symbol, onDeals)

    # ----------------------------------------------------------------------
    def subscribeKlines(self, symbol, period, onKlines):
        channel = 'ok_sub_spot_%s_kline_%s' % (self.transOkSymbol(symbol), period)
        self.subTopic({'event':'addChannel','channel':channel})
        super(okex,self).subscribeKlines(symbol, period, onKlines)

    # ----------------------------------------------------------------------
    def subscribeOrders(self, symbol, onOrders):
        """订阅委托推送"""
        if not self.logined: self.login()
        channel = 'ok_sub_spot_%s_order' % self.transOkSymbol(symbol)
        self.subTopic({'event':'addChannel','channel':channel})
        super(okex,self).subscribeOrders(symbol, onOrders)

    # ----------------------------------------------------------------------
    def subscribeBalance(self, symbol, onBalance):
        if not self.logined: self.login()
        """订阅资金推送"""
        channel = 'ok_sub_spot_%s_balance' % self.transOkSymbol(symbol)
        self.subTopic({'event':'addChannel','channel':channel})
        super(okex,self).subscribeBalance(symbol, onBalance)

if __name__ == '__main__':
    def onDepth(symbol, data):
        print("--",symbol, data)
    def onOrders(symbol, data):
        print("onOrders:",symbol,data)



    #wss = okex({
    #    'apiKey':'a2a39a1a-8220-42a0-bfd6-16b65ae808a7',
    #    'secret':'61C17ED2F39D9324A7DC8D03DA56DD5B'})
    wss = okex()
    #wss.fetch_trades('BTC/USDT')
    #wss.subscribeTicker('ZRX/ETH',onDepth)
    wss.start()
    wss.subscribeDepth('BTC/USDT', onDepth)
    #wss.apiKey = getattr(accountConfig, 'OKEX')['CNY_1']['ACCESS_KEY']
    #wss.secret = getattr(accountConfig, 'OKEX')['CNY_1']['SECRET_KEY']
    #wss.subscribeDepth('BTC/USDT',onDepth)
    #wss.subscribeOrders('KCASH/ETH', onOrders)
    #wss.subscribeBalance('KCASH/ETH', onDepth)
    #wss.subscribeDeals('BTC/USDT', onDepth)
    #orderBook = wss.fetch_order_book('KCASH/ETH')
    #b = wss.fetch_balance()
    #print ('kcash: %s, eth: %s'%(b['KCASH'],b['ETH']))
    #order = wss.create_order('KCASH/ETH','limit','buy', 10, orderBook['asks'][0][0])
    #print('order:',order)
    #orders = wss.fetch_open_orders('KCASH/ETH')
    #for order in orders:
    #    print(wss.cancel_order(order['id'],'KCASH/ETH'))

