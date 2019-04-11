import json
import math
import time
import arrow
from decimal import *
import ccxt

from priceserver.common.logger import *

log = getLog('stat')
logError = getLog('error')
from ccxt.base.errors import *
from bytetradeLib.bytetradelib import *
import requests

curDir = os.path.dirname(__file__)
BYTETRADE_API = 'https://api.bytetrade.io'

dapp = 'Sagittarius'
# BTT价格更新周期：5分钟
BTT_UPDATE_TIME = 300
# 额外抵押的BTT
BTT_EXTRA = 2
BTT_FEE_RATE = 0.0005


class ccxtBytetrade(ccxt.Exchange):
    def __init__(self, config={}):
        config.update({'id': 'bytetrade'})
        ccxt.Exchange.__init__(self, config)
        self.bttPrice = {}
        self.urlprex = config.get('apiUrl')
        self.pixiu_urlprex = ''
        if self.urlprex == None:
            self.urlprex = BYTETRADE_API + '/bittrade/v1/me'
        self.assets = {}
        self.marketData = {}

    def describe(self):
        return self.deep_extend(super(ccxtBytetrade, self).describe(), {
            'id': 'bytetrade',
            'name': 'ByteTrade',
            'countries': ['CN', 'US'],
            'version': 'v1',
            'rateLimit': 1000,
            # up to 3000 requests per 5 minutes ≈ 600 requests per minute ≈ 10 requests per second ≈ 100 ms
            'has': {
                'fetchTickers': True,
                'withdraw': True,
            }})

    def getAsset(self, asset, id):
        assetObj = None
        self.__getAssets()
        id = str(id)
        if id and self.assets:
            for i in self.assets:
                if id == self.assets[i]['id']:
                    assetObj = self.assets[i]['info']
                    if assetObj['asset'] == 'BTT':
                        assetObj['external_precision'] = 1000000000000
                    break
        else:
            asset = asset.lower()
            for i in self.assets:
                if asset == self.assets[i]['info']['asset'].lower():
                    assetObj = self.assets[i]['info']
                    if assetObj['asset'] == 'BTT':
                        assetObj['external_precision'] = 1000000000000
                    break
        return assetObj

    def getPixiuAddress(self):
        if ("https://c" in self.urlprex or "test" in self.urlprex):
            self.pixiu_urlprex = "http://newton.bytetrade.com/pixiu/api/v1"
        else:
            self.pixiu_urlprex = "https://pixiu.bytetrade.com/api/v1"

        url = self.pixiu_urlprex + '?cmd=requestAddress&userid=' + self.apiKey
        res = requests.post(url)
        return res.json()

    def getBasePrec(self, asset, id=None):
        asset = self.getAsset(asset, id)
        if (asset):
            return asset['base_precision']
        return 0

    def getMinTradeAmount(self, asset, id=None):
        assetObj = self.getAsset(asset, id)
        if (assetObj):
            return assetObj['min_trade_amount']
        return 0

    def calcAmountString(self, amount, symbolId):
        minAmount = self.getMinTradeAmount(None, symbolId)
        basePrec = self.getBasePrec(None, symbolId)
        newAmount = int(Decimal(amount) * basePrec / minAmount) * minAmount
        if newAmount < minAmount:
            return '0'
        return str(newAmount)

    def getAmountPrecBySymbol(self, market):
        def eq(item):
            return item['name'] == market

        if not self.marketData:
            self.marketData = self.fetch_btt_markets()
        marketInfo = list(filter(eq, self.marketData))
        if len(marketInfo) > 0:
            #            return marketInfo[0]['defaultEthPrec']
            t = self.getBasePrec(market.split('/')[1])
            for i in range(0, marketInfo[0]['stockPrec']):
                t = t / 10
            return t
        return int(math.log10(self.getMinTradeAmount(market.split('/')[1])))

    def getPricePrecBySymbol(self, market):
        def eq(item):
            return item['name'] == market

        if not self.marketData:
            self.marketData = self.fetch_btt_markets()
        marketInfo = list(filter(eq, self.marketData))
        if len(marketInfo) > 0:
            t = self.getBasePrec(market.split('/')[0])
            for i in range(0, marketInfo[0]['moneyPrec']):
                t = t / 10
            return t
        return int(math.log10(self.getMinTradeAmount(market.split('/')[0])))

    def getAmountPrecById(self, marketId):
        def eq(item):
            return '/'.join([str(item['stockId']), str(item['moneyId'])]) == marketId

        if not self.marketData:
            self.marketData = self.fetch_btt_markets()
        marketInfo = list(filter(eq, self.marketData))
        if len(marketInfo) > 0:
            #            return marketInfo[0]['defaultEthPrec']
            t = self.getBasePrec(None, marketId.split('/')[1])
            for i in range(0, marketInfo[0]['stockPrec']):
                t = t / 10
            return t
        return int(math.log10(self.getMinTradeAmount(None, marketId.split('/')[1])))

    def getPricePrecById(self, marketId):
        def eq(item):
            return '/'.join([str(item['stockId']), str(item['moneyId'])]) == marketId

        if not self.marketData:
            self.marketData = self.fetch_btt_markets()
        marketInfo = list(filter(eq, self.marketData))
        if len(marketInfo) > 0:
            t = self.getBasePrec(None, marketId.split('/')[0])
            moneyPrec = min(marketInfo[0]['moneyPrec'], 8)
            for i in range(0, moneyPrec):
                t = t / 10
            return t
        return int(math.log10(self.getMinTradeAmount(None, marketId.split('/')[0])))

    def __getAssets(self):
        if not self.assets:
            self.assets = self.fetch_balance_full()
        return self.assets

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

    def parse_order(self, order, market=None):
        status = 'open'
        remaining = float(order.get('left', 0))
        amount = float(order['amount'])
        filled = amount - remaining
        cOrder = {
            'info': order,
            'id': order['orderid'],
            'timestamp': str(arrow.get(order['createTime'])),
            'datetime': time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(float(order['createTime']))),
            'lastTradeTimestamp': str(arrow.get(order.get("finishTime", None))),
            'pair': order['market'],
            'symbol': order['marketId'],
            'type': 'limit' if order['type'] == 'LIMIT' else 'market',
            'side': 'sell' if order['side'] == 'SELL' else 'buy',
            'price': float(order['price']),
            'average': 0,
            'cost': float(order['dealMoney']),
            'amount': amount,
            'filled': filled,
            'remaining': remaining,
            'status': status,
            'fee': float(order['fee']),
            'bttFee': float(order.get('freezeBttFee', 0)),
            "exchange_name": "bytetrade",
        }
        return cOrder

    def fetch_btt_markets(self):
        url = self.urlprex + '?cmd=markets'
        res = self.fetch(url)
        if res['code'] == 0:
            return res['symbols']
        return None

    def fetch_ohlcv(self, symbol, timeframe='1m', since=None, limit=None, params={}):
        bttTimeFrame = timeframe.upper()
        url = self.urlprex + '?cmd=klineData&symbol=' + symbol + '&resolution=' + bttTimeFrame + '&to=' + str(
            arrow.now().timestamp)
        res = self.fetch(url)
        ret = []
        if res['s'] == "ok":
            kDataLen = len(res['t'])
            for i in range(0, kDataLen):
                ret.append(
                    [res['t'][i] * 1000, float(res['o'][i]), float(res['h'][i]), float(res['l'][i]), float(res['c'][i]),
                     float(res['v'][i])])
        return self.sort_by(ret, 0)

    def parse_balance(self, balance):
        ret = {}
        if self.assets:
            ret['free'] = float(balance['available']) if self.calcAmountString(balance['available'],
                                                                               balance['id']) != '0' else 0
            ret['used'] = float(balance['freeze']) if self.calcAmountString(balance['freeze'],
                                                                            balance['id']) != '0' else 0
            total = ret['free'] + ret['used']
            ret['total'] = total if self.calcAmountString(total, balance['id']) != '0' else 0
        else:
            ret['free'] = float(balance['available'])
            ret['used'] = float(balance['freeze'])
            total = ret['free'] + ret['used']
            ret['total'] = total
        ret['id'] = str(balance['id'])
        ret['info'] = balance
        return ret

    def __fetch_balance_url(self, url, params={}):
        asset = '&asset=' + ','.join(params['symbol']) if params.get('symbol') else ''
        url += asset
        res = self.fetch(url)
        if res['code'] != 0:
            logError.error('error in fetch_balance: %s, url %s' % (res, url))
            time.sleep(0.5)
            return self.__fetch_balance_url(url)
        resBalance = res.get('balances')
        if not resBalance:
            logError.error('blank data in fetch_balance: %s, url %s' % (res, url))
            time.sleep(0.5)
            return self.__fetch_balance_url(url)
        balances = {str(b['id']): self.parse_balance(b) for b in resBalance}
        return balances

    def fetch_balance_full(self, params={}):
        url = self.urlprex + '?cmd=listAccounts&userid=' + self.apiKey + '&channel=all'
        return self.__fetch_balance_url(url, params)

    def fetch_balance(self, params={}):
        url = self.urlprex + '?cmd=listAccounts&userid=' + self.apiKey + '&channel=all'
        return self.__fetch_balance_url(url, params)

    def fetch_order(self, id, symbol=None, params={}):
        if symbol is None:
            raise ExchangeError(self.apiKey + ' fetchOrder requires a symbol parameter')
        url = self.urlprex + '?cmd=orderStatus&userid=%s&orderid=%s' % (self.apiKey, id)
        res = self.fetch(url)
        return self.parse_order(res['result'])

    def get_market_id(self, symbol):
        if not self.marketData:
            self.marketData = self.fetch_btt_markets()
        marketId = None
        if symbol is not None:
            symbolPair = symbol.split('/')
            for d in self.marketData:
                if str(d['stockId']) == symbolPair[0] and str(d['moneyId']) == symbolPair[1]:
                    marketId = d['id']
                    break
        return marketId

    def fetch_open_orders(self, symbol=None, since=None, limit=None, params={}):
        marketId = self.get_market_id(symbol)
        marketParam = '' if marketId == None else '&market=' + str(marketId)
        res = self.fetch(self.urlprex + '?cmd=openOrders&userid=' + self.apiKey + '&offset=0&limit=100' + marketParam)
        return self.parse_orders(res['result'])

    def fetch_finished_orders(self, symbol=None, since=None, limit=None, params={}):
        orders = []
        marketId = self.get_market_id(symbol)
        marketParam = '' if marketId == None else '&market=' + str(marketId)
        res = self.fetch(
            self.urlprex + '?cmd=finishedOrders&userid=' + self.apiKey + '&offset=0&limit=100' + marketParam)
        for order in res["result"]:
            ccxt_order = self.parse_order(order)
            ccxt_order["average"] = ccxt_order["cost"] / ccxt_order["filled"]
            ccxt_order["status"] = "closed"
            orders.append(ccxt_order)
        return orders
        # return self.parse_orders(res['result'])

    def fetch_order_book(self, symbol, limit=None, params={}):
        limitString = '' if not limit else '&limit=%d' % limit
        marketId = self.get_market_id(symbol)
        res = self.fetch(self.urlprex + '?cmd=depthData&symbol=%s%s' % (str(marketId), limitString))
        return self.parse_order_book(res['result'])

    def parse_ticker(self, ticker, market=None):
        # {"name": "ETH/BTT", # 交易对名称
        #     "today": {
        #             "deal": "19287095886.927747265582", # 24H amount
        #             "high": "1386535.4523",# Highest price
        #             "last": "1221127.4196", # Latest price
        #             "low": "1216964.1849", # Lowest price
        #             "open": "1346291.5386", # Open today
        #             "volume": "14728.50161761", # 24H volume
        #             "change": 15.5 #涨跌幅度>0代表涨,<0代表跌
        #     }
        # }
        today = ticker['today']
        last = self.safe_float(today, 'last')
        now = arrow.now()
        return {
            'symbol': ticker["name"],
            'timestamp': now.timestamp,
            'datetime': str(now),
            'high': self.safe_float(today, 'high'),
            'low': self.safe_float(today, 'low'),
            'bid': last,
            'bidVolume': None,
            'ask': last,
            'askVolume': None,
            'vwap': None,
            'open': self.safe_float(today, 'open'),
            'close': last,
            'last': last,
            'previousClose': None,
            'change': None,
            'percentage': self.safe_float(today, 'change'),
            'average': None,
            'baseVolume': self.safe_float(today, 'volume'),
            'quoteVolume': None,
            'info': ticker,
        }

    def parse_tickers(self, tickers, market=None):
        return {ticker['name']: self.parse_ticker(ticker) for ticker in tickers}

    # 过去24小时交易信息 */
    def fetch_tickers(self, symbols=None, params={}):
        symbolUrl = ''
        if symbols: symbolUrl = '&symbol=' + symbols
        res = self.fetch(self.urlprex + '?cmd=marketsPrice' + symbolUrl)
        if res['code'] == 0:
            return self.parse_tickers(res['result'])
        return None

    def fetch_ticker(self, symbol):
        res = self.fetch(self.urlprex + '?cmd=marketsPrice&symbol=' + symbol)
        if res['code'] == 0 and res['result']:
            return self.parse_ticker(res['result'][0])
        return None

    def getBttPrice(self, bttSymbol):
        if bttSymbol not in self.bttPrice or self.bttPrice[bttSymbol]['price'] <= 0 or arrow.now().timestamp - \
                self.bttPrice[bttSymbol]['time'] > BTT_UPDATE_TIME:
            ticker = self.fetch_ticker(bttSymbol)
            self.bttPrice[bttSymbol] = {}
            if ticker:
                self.bttPrice[bttSymbol]['price'] = ticker['last'] if ticker['last'] else 0
                self.bttPrice[bttSymbol]['time'] = arrow.now().timestamp
            else:
                self.bttPrice[bttSymbol]['price'] = 0
                self.bttPrice[bttSymbol]['time'] = 0
        return self.bttPrice[bttSymbol]['price']

    def getFreezeBttFee(self, stockAsset, moneyAsset, side, orderType, amount, price):
        if side == 'sell':
            bttPrice = self.getBttPrice(stockAsset + '/1')
            bttFeeRequire = amount * bttPrice
        else:
            bttPrice = self.getBttPrice(moneyAsset + '/1')
            bttFeeRequire = amount * price * bttPrice
            if orderType == 2:
                bttFeeRequire = amount * bttPrice
        minTrade = int(bttFeeRequire * BTT_FEE_RATE * BTT_EXTRA * 1000000000000000000 / 100000000 + 1)
        return minTrade * 100000000

    def formatBttSymbol(self, pair):
        if not self.marketData:
            self.marketData = self.fetch_btt_markets()
        bttSymbol = {}
        symbolPair = pair.split('/')
        stockSymbol = symbolPair[0].split('_')
        moneySymbol = symbolPair[1].split('_')
        bttSymbol['stockSymbol'] = stockSymbol[0]
        bttSymbol['moneySymbol'] = moneySymbol[0]
        if len(stockSymbol) > 1:
            bttSymbol['stockId'] = stockSymbol[1]
            for market in self.marketData:
                if market['name'] == bttSymbol['stockSymbol'] + '/' + bttSymbol['moneySymbol'] and market['stockId'] == \
                        bttSymbol['stockId']:
                    bttSymbol['moneyId'] = market['moneyId']
                    break
        if len(moneySymbol) > 1:
            bttSymbol['moneyId'] = stockSymbol[1]
            for market in self.marketData:
                if market['name'] == bttSymbol['stockSymbol'] + '/' + bttSymbol['moneySymbol'] and market['moneyId'] == \
                        bttSymbol['moneyId']:
                    bttSymbol['stockId'] = market['stockId']
                    break
        return bttSymbol

    def id_to_symbol(self, pair, real=False):
        if not self.marketData:
            self.marketData = self.fetch_btt_markets()
        if pair is not None:
            symbolPair = pair.split('/')
            stockName = ''
            moneyName = ''
            for d in self.marketData:
                if real:
                    if str(d['stockId']) == symbolPair[0] and str(d['moneyId']) == symbolPair[1]:
                        return d['name']
                else:
                    if str(d['stockId']) == symbolPair[0]:
                        stockName = d['stock']
                    if str(d['moneyId']) == symbolPair[1]:
                        moneyName = d['money']
                    if stockName and moneyName:
                        return f'{stockName}/{moneyName}'
        return None

    def create_order(self, symbol, type, side, amount, price=None, params={}):

        pass

    def cancel_order(self, id, symbol=None, params={}):

        pass

    def transfer(self, targetId, symbolId, amount, message=None):

        pass

    def createUser(self, id, privateKey):

        pass

    def withdraw(self, code, amount, address, tag=None, params={}):

        pass


if __name__ == '__main__':
    ex = ccxtBytetrade({
        'apiKey': 'kcInvestor',
        'secret': '24160d89b4aa511009ee27bf453d87a76f7b9b911710dde7b98f2d07f98ebadd',
        'apiUrl': 'https://c3.bytetrade.io/bittrade/v1/me'
    })
    # ex.fetch_open_orders()
    ex.create_order("6/2", "limit", "buy", 100, 0.00001)
    # ex.fetch_finished_orders()
    # if hasattr(ex,'idToSymbol'):
    #     print('yes')
    # else:
    #     print('no')
    # b = ex.fetch_order_book('4/2')
    # print (b)
    # ex.transfer('hw19820211', '1', 0.01)
    # b = ex.fetch_tickers()
    # b = ex.fetch_ohlcv('KCASH/ETH','1d')
    # print(b)
    # print(ex.getAmountPrec('ETH/LRT'))
    # print(ex.getPricePrec('ETH/LRT'))

    # b = ex.create_order('10/3', 'limit', 'sell', 1.01234567890123456789, 0.123456789123456789123456789)
    # ex.transfer('softgaga','3',0.123456789123456789123456789)
    # print(ex.getPricePrecById('3/2'))
    # print(ex.getPricePrecBySymbol('KCASH/ETH'))
    # print(b)
