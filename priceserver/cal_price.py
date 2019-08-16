# -*- coding: utf-8 -*-
# Author: zhangchao
# Date: 2019/3/14
# Desc: 获取各个交易所的symbol的图并计算路径和价格
import sys

sys.path.append("..")

from priceserver.common.logger import getLog
from priceserver.common.db_connection import ConnectRedis

logger = getLog()

import time

INF_val = 9999


class Floyd_Path():
    def __init__(self, node, node_map, path_map):
        self.node = node
        self.node_map = node_map
        self.node_length = len(node_map)
        self.path_map = path_map
        self._init_Floyd()

    def __call__(self, from_node, to_node):
        self.from_node = from_node
        self.to_node = to_node
        return self._format_path()

    def _init_Floyd(self):
        for k in range(self.node_length):
            for i in range(self.node_length):
                for j in range(self.node_length):
                    tmp = self.node_map[i][k] + self.node_map[k][j]
                    if self.node_map[i][j] > tmp:
                        self.node_map[i][j] = tmp
                        self.path_map[i][j] = self.path_map[i][k]

        # print('_init_Floyd is end')

    def _format_path(self):
        node_list = []
        temp_node = self.from_node
        obj_node = self.to_node
        print(f"the shortest path is: {self.node_map[temp_node][obj_node]}")
        node_list.append(self.node[temp_node])
        while True:
            node_list.append(self.node[self.path_map[temp_node][obj_node]])
            temp_node = self.path_map[temp_node][obj_node]
            if temp_node == obj_node:
                break

        return node_list


def set_node_map(node_map, node, node_list, path_map):
    for i in range(len(node)):
        ## 对角线为0
        node_map[i][i] = 0
    for x, y, val in node_list:
        node_map[node.index(x)][node.index(y)] = node_map[node.index(y)][node.index(x)] = val
        path_map[node.index(x)][node.index(y)] = node.index(y)
        path_map[node.index(y)][node.index(x)] = node.index(x)


class CalPrice(object):
    def __init__(self, bytetrade_price, huobi_price, coinbase_price):
        # 初始化图
        self.r = ConnectRedis()
        self.bytetrade_price = bytetrade_price
        self.huobi_price = huobi_price
        self.coinbase_price = coinbase_price

    def get_symbols(self):
        """
        获取redis中保存的交易所的所有币对
        :param exchange_name: 交易所名称，huobipro， bytetrade
        :return: 交易所支持的币对的列表
        """
        redis_key_huobi = "price_server_huobipro1"
        redis_key_bytetrade = "price_server_bytetrade1"
        symbols_huibo = list(self.r.hgetall(redis_key_huobi).keys())
        symbols_bytetrade = list(self.r.hgetall(redis_key_bytetrade).keys())
        res = list(self.r.hgetall("coinbase_currency_price1"))

        symbols = list(set(symbols_huibo + symbols_bytetrade + res))
        return symbols

    def cal_price(self, path):
        # 拼接成交易对
        # print(path)
        if path:
            symbols = []
            for i in range(len(path)):
                if i + 1 == len(path):
                    pass
                else:
                    symbol = path[i] + "/" + path[i + 1]
                    symbols.append(symbol)

            dic = {}

            def get_price(symbol):
                # price_bytetrade = self.r.hget(key_bytetrade, symbol)
                # price_huobipro = self.r.hget(key_huobipro, symbol)
                # price_coinbase = self.r.hget(key_coin_base, symbol)
                price_bytetrade = self.bytetrade_price.get(symbol, 0)
                price_huobipro = self.huobi_price.get(symbol, 0)
                price_coinbase = self.coinbase_price.get(symbol, 0)

                if price_bytetrade and price_bytetrade != 0:
                    price = float(price_bytetrade)
                else:
                    if price_huobipro and price_huobipro != 0:
                        price = float(price_huobipro)
                    else:
                        if price_coinbase and price_coinbase != 0:
                            price = float(price_coinbase)
                        else:
                            return 0
                return price

            for symbol in symbols:
                # 币币价格
                price = get_price(symbol)

                if price:
                    dic[symbol] = price
                else:
                    t1, t2 = symbol.split("/")
                    reverse_symbol = t2 + "/" + t1
                    price = get_price(reverse_symbol)
                    if price:
                        if float(price) == 0:
                            dic[symbol] = 0
                        else:
                            dic[symbol] = 1 / float(price)
                    else:
                        dic[symbol] = 0

            res = 1
            for i in dic.values():
                res *= float(i)
        else:
            # logger.info("交易对没有路径，返回价格为0")
            res = 0
        return res

    def search(self, symbols, start, end):

        temp = []
        node_list = []

        for i in symbols:
            stock = i.split("/")[0]
            money = i.split("/")[1]
            temp.append(stock)
            temp.append(money)
            t = (stock, money, 1)
            node_list.append(t)
        node = list(set(temp))
        ## node_map[i][j] 存储i到j的最短距离
        node_map = [[INF_val for val in range(len(node))] for val in range(len(node))]
        ## path_map[i][j]=j 表示i到j的最短路径是经过顶点j
        path_map = [[0 for val in range(len(node))] for val in range(len(node))]

        ## set node_map
        set_node_map(node_map, node, node_list, path_map)
        ## select one node to obj node, e.g. A --> D(node[0] --> node[3])
        from_node = node.index(start)
        to_node = node.index(end)
        Floydpath = Floyd_Path(node, node_map, path_map)
        path = Floydpath(from_node, to_node)

        return path

    def calculate_price(self, start, end, mid=None):
        # 从缓存中获取路径

        try:
            if mid:
                key = start + "_" + mid + "_" + end
                path = self.r.hget("price_server_path1", key)

            else:
                key = start + "_" + end
                path = self.r.hget("price_server_path1", key)

            if path:
                path = eval(path)
            else:
                # 缓存中没有，就计算路径并加入缓存
                if mid:
                    path = self.search(self.get_symbols(), mid, end)
                    path = [start] + path
                else:
                    path = self.search(self.get_symbols(), start, end)

                self.r.hset("price_server_path1", key, str(path))
            print(path)
            price = self.cal_price(path)
            # print(price)
            return price
        #
        except:
            logger.info(f"{start, end, mid}找不到这个路径")
            return 0


if __name__ == '__main__':
    pass
    # symbols = get_symbols_from_exchange("bytetrade")
    # total_graph = get_total_graph("huobipro")
    # total_graph = get_total_graph("bytetrade")
    # exchange = "bytetrade"
    # # exchange = "huobipro"
    # print(total_graph)
    # # # t1 = time.time()
    # print(path)
    # # t2 = time.time()
    # # print(t2 - t1)
    # print(path)
    # price = cal_price(['HLB', 'USD'])
    # print(get_total_graph())
    # price1 = calculate_price("HLB", "ETH", "CNY")
    # t1 = time.time()
    # price2 = calculate_price("HLB", "BTC", "GBP")
    # price2 = calculate_price("HLB", "BTC", "USD")
    # price2 = calculate_price("HLB", "BTC", "CNY")
    # print(price2)
    # t2 = time.time()
    # print(f"time{t2 - t1}")
    # print(price2)
    # print(price)
    # print(get_total_graph())
    # path = search(get_total_graph(), "HLB", "BTC", "USD")
    # print(path)
    # pass
    # 图
    # t1 = time.time()
    # print(symbol_graph(get_symbols()))
    # t2 = time.time()
    # print(t2 - t1)
    #
    # pass
    # from priceserver.conf.settings import CURRENCY_LIST

    # r = ConnectRedis()
    # for i in CURRENCY_LIST:
    #     key = "HLB_" + i
    #     r.hdel("price_server_path1", key)
    # r.delete("price_server_path1")
    # for i in SYMBOL_LIST:
    #     for j in CURRENCY_LIST:

            # price = calprice.calculate_price(i, j)
            # print(price)
    # print(price)
    #         # print(price)
    # price = calprice.calculate_price("USD", "USDT")
    # print(price)

# t2 = time.time()
    # print(t2 - t1)
    # print(price)
    # pass
