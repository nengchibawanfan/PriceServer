# -*- coding: utf-8 -*-
# Author: zhangchao
# Date: 2019/3/14
# Desc: 获取各个交易所的symbol的图
import sys
from collections import deque

from priceserver.conf.settings import CURRENCY_LIST

sys.path.append("..")

from priceserver.commen.db_connection import ConnectRedis

r = ConnectRedis()


def get_symbols_from_exchange(exchange_name):
    """
    获取redis中保存的交易所的所有币对
    :param exchange_name: 交易所名称，huobipro， bytetrade
    :return: 交易所支持的币对的列表
    """
    redis_key = "price_server_" + exchange_name
    symbols = list(r.hgetall(redis_key).keys())
    return symbols


def get_currency_price():
    res = list(r.hgetall("coinbase_currency_price"))
    return res


def symbol_graph(symbols):
    # 绘制出交易币种图
    res = {}
    for symbol in symbols:
        stock, money = symbol.split("/")
        try:
            res[stock].add(money)
        except:
            res[stock] = set()
            res[stock].add(money)
        try:
            res[money].add(stock)
        except:
            res[money] = set()
            res[money].add(stock)
    return res


def get_total_graph(exchange):
    symbols = get_symbols_from_exchange(exchange)
    symbols_graph = symbol_graph(symbols)
    cu = get_currency_price()

    for i in cu:
        coin, currency = i.split("/")

        if coin in symbols_graph.keys():
            symbols_graph[coin].add(currency)

            if currency in symbols_graph.keys():
                symbols_graph[currency].add((coin))
            else:
                symbols_graph[currency] = set()
                symbols_graph[currency].add(coin)

    return symbols_graph


def search(graph, start, mid, end, path=[]):
    if mid in graph[end]:
        return [start, mid, end]
    else:
        # 创建搜索队列
        search_queue = deque()
        # 初始化搜索队列
        path = path + [start]
        search_queue += [start]
        # 记录已经搜索过的node
        searched = []
        # 只要队列不空就一直搜索
        next_paths = []
        while search_queue:
            # 取出队列中最先加进去的一个node
            node = search_queue.popleft()

            if not node in searched:
                # 查看是不是结束点
                if next_paths:
                    for p in next_paths:
                        if p[-1] == node:
                            next_paths.remove(p)
                            path = p

                if node_is_end(node, end, path):
                    return path
                else:
                    # 不是结束,所以将他的点都加入搜索队列
                    search_queue += graph[node]
                    # 标记这个点已经被搜索过了
                    searched.append(node)
                    # 把这个点和node拼接为路径
                    temp = []
                    for i in next_paths:
                        for j in i:
                            temp.append(j)

                    next_paths = next_paths + [path + [i] for i in graph[node] if i not in temp]

    return False


def node_is_end(node, end, path):
    if node == end:
        #
        return True
    else:
        return False


def cal_price(exchange, path):
    # 拼接成交易对
    if path:
        symbols = []
        for i in range(len(path)):
            if i + 1 == len(path):
                pass
            else:
                symbol = path[i] + "/" + path[i + 1]
                symbols.append(symbol)

        key = "price_server_" + exchange

        dic = {}

        for symbol in symbols:
            # 币币价格
            price = r.hget(key, symbol)
            if price:
                dic[symbol] = price
            else:
                t1, t2 = symbol.split("/")
                reverse_symbol = t2 + "/" + t1
                price = r.hget(key, reverse_symbol)
                if price:
                    if float(price) == 0:
                        dic[symbol] = 0
                    else:
                        dic[symbol] = 1 / float(price)
                else:
                    dic[symbol] = 0

        if path[-1] in CURRENCY_LIST:
            cu_price = r.hget("coinbase_currency_price", symbols[-1])
            if cu_price:
                dic[symbols[-1]] = cu_price
            else:
                dic[symbols[-1]] = 0

        res = 1
        for i in dic.values():
            res *= float(i)
    else:
        res = 0
    return res


def calculate_price(exchange, start, mid, end):
    key = start + "_" + mid + "_" + end + "_" + exchange
    path = r.hget("price_server_path", key)
    # 从缓存中获取路径
    if path:
        path = eval(path)
    else:
        # 缓存中没有，就计算路径并加入缓存
        total_graph = get_total_graph(exchange)
        path = search(total_graph, start, mid, end)
        r.hset("price_server_path", key, str(path))
    price = cal_price(exchange, path)
    return price


if __name__ == '__main__':
    # symbols = get_symbols_from_exchange("bytetrade")
    # total_graph = get_total_graph("huobipro")
    total_graph = get_total_graph("huobipro")
    # print(total_graph)

    path = search(total_graph, "KCASH", "BTC", "CNY")
    print("path")
    print(path)
    price = cal_price("huobipro", path)
# price = calculate_price("huobipro", "MT", "CNY")
    print(price)
#
