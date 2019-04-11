# -*- coding: utf-8 -*-
# Author: zhangchao
# Date: 2019/3/14
# Desc: 获取各个交易所的symbol的图并计算路径和价格
import sys
import time

from collections import deque

sys.path.append("..")

from priceserver.common.logger import getLog
from priceserver.conf.settings import CURRENCY_LIST
from priceserver.common.db_connection import ConnectRedis

r = ConnectRedis()
logger = getLog()


def get_symbols_from_exchange():
    """
    获取redis中保存的交易所的所有币对
    :param exchange_name: 交易所名称，huobipro， bytetrade
    :return: 交易所支持的币对的列表
    """
    redis_key_huobi = "price_server_huobipro"
    redis_key_bytetrade = "price_server_bytetrade"
    symbols_huibo = list(r.hgetall(redis_key_huobi).keys())
    symbols_bytetrade = list(r.hgetall(redis_key_bytetrade).keys())
    symbols = list(set(symbols_huibo + symbols_bytetrade))
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


def get_total_graph():
    # graph = r.hget("price_server_graph", exchange)
    # # 看有没有这个交易所的图的缓存
    # if graph:
    #     symbols_graph = eval(graph)
    # else:
    symbols = get_symbols_from_exchange()
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

    # r.hset("price_server_graph", exchange, str(symbols_graph))

    return symbols_graph


def search(graph, start, mid, end, path=[]):
    if mid in graph[start]:
        if mid in graph[end]:
            return [start, mid, end]
    else:
        # 创建搜索队列
        search_queue = deque()
        # 初始化搜索队列
        path = path + [start]
        print(path)
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


def cal_price(path):
    # 拼接成交易对
    if path:
        symbols = []
        for i in range(len(path)):
            if i + 1 == len(path):
                pass
            else:
                symbol = path[i] + "/" + path[i + 1]
                symbols.append(symbol)

        key_bytetrade = "price_server_bytetrade"
        key_huobipro = "price_server_huobipro"

        dic = {}
        def get_price(symbol):
            price_bytetrade = r.hget(key_bytetrade, symbol)
            price_huobipro = r.hget(key_huobipro, symbol)

            if price_bytetrade:
                price = price_bytetrade
            else:
                if price_huobipro:
                    price = price_huobipro
                else:
                    return False

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
        logger.info("交易对没有路径，返回价格为0")
        res = 0
    return res


def calculate_price(start, mid, end):

    # 从缓存中获取路径

    try:
        # if price == 0:
        key = start + "_" + mid + "_" + end
        path = r.hget("price_server_path", key)
        if path:
            path = eval(path)
        else:
            # 缓存中没有，就计算路径并加入缓存
            total_graph = get_total_graph()
            path = search(total_graph, start, mid, end)
            if mid in path:
                r.hset("price_server_path", key, str(path))
        price = cal_price(path)
        # else:
        #     price = price
    except:
        logger.info(f"{start, mid, end}找不到这个路径")

    try:
        if price == 0:
            key = start + "_" + mid + "_" + end + "_" + "bytetrade"
            path = r.hget("price_server_path", key)
            if path:
                path = eval(path)
            else:
                # 缓存中没有，就计算路径并加入缓存
                total_graph = get_total_graph()
                path = search(total_graph, start, mid, end)
                if mid in path:
                    r.hset("price_server_path", key, str(path))
            price = cal_price(path)
        else:
            price = price
    except:
        price = 0

    return price


if __name__ == '__main__':
    # symbols = get_symbols_from_exchange("bytetrade")
    # total_graph = get_total_graph("huobipro")
    # total_graph = get_total_graph("bytetrade")
    # exchange = "bytetrade"
    # # exchange = "huobipro"
    # print(total_graph)
    # # # t1 = time.time()
    # path = search(total_graph, "MT", "BTC", "CNY")
    # print(path)
    # # t2 = time.time()
    # # print(t2 - t1)
    # print(path)
    # price = cal_price(exchange, path)
    price = calculate_price("MT", "BTC", "CNY")
    print(price)
    # print(price)
    # print(get_total_graph())

#
