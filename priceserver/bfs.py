# -*-coding:utf-8-*-
import sys
from collections import deque

from priceserver.common.db_connection import ConnectRedis

r = ConnectRedis()


def search(graph, start, end, path=[]):
    # 创建搜索队列
    search_queue = deque()
    path = path + [start]
    # 初始化搜索队列
    search_queue += graph[start]
    # 记录已经搜索过的node
    searched = []
    searched.append(start)
    # 只要队列不空就一直搜索
    while search_queue:
        # 取出队列中最先加进去的一个node
        node = search_queue.popleft()

        # 只有他没有被搜索过才进行搜索
        if not node in searched:
            # 查看是不是结束点

            path += [node]

            if node_is_end(node, end, path):

                return node_is_end(node, end, path)
            else:
                # 不是结束,所以将他的点都加入搜索队列
                search_queue += graph[node]
                # 标记这个人已经被搜索过了
                searched.append(node)

    return False


def node_is_end(node, end, path):
    if node == end:
        for index, value in enumerate(path):
            if node in graph[value]:
                path = path[0: index + 1] + [path[-1]]
                # 判断该路径是否可用
                return path
    else:
        return False


def cal_price(exchange, path):
    # 拼接成交易对

    symbols = []
    for i in range(len(path)):
        if i + 1 == len(path):
            pass
        else:
            symbol = path[i] + "/" + path[i + 1]
            symbols.append(symbol)

    # 判断redis中有没有存这个报价   只要有一个为0，就返回0
    key = "price_server_" + exchange
    dic = {}
    for symbol in symbols[0: -1]:
        # 币币价格
        price = r.hget(key, symbol)
        if price:
            dic[symbol] = price
        else:
            t1, t2 = symbol.split("/")
            reverse_symbol = t2 + "/" + t1
            price = r.hget(key, reverse_symbol)
            if price:
                dic[symbol] = 1 / float(price)
            else:
                dic[symbol] = 0
    cu_price = r.hget("coinbase_currency_price", symbols[-1])
    if cu_price:
        dic[symbols[-1]] = cu_price
    else:
        dic[symbols[-1]] = 0

    res = 1
    for i in dic.values():
        res *= float(i)

    return res


if __name__ == '__main__':
    # 用散列表实现图
    graph = {
        'KCASH': {'MANA', 'BLZ', 'CMT', 'WISH', 'APPC', 'OMG', 'ENG', 'ETH', 'ELF', 'BAT', 'ZIL', 'ADX', 'BTM', 'KEX',
                  'ONOT', 'ZRX', 'IOST', 'BNB', 'TNB', 'WTC', 'AE', 'VROS', 'DGD', 'MCO', 'SNT', 'THETA', 'GNT'},
        'ETH': {'MANA', 'BLZ', 'CMT', 'APPC', 'ENG', 'OMG', 'ELF', 'KCASH', 'BAT', 'GUSD', 'ZIL', 'ADX', 'BTM', 'KEX',
                'ONOT', 'BWL', 'ZRX', 'IOST', 'USD', 'BNB', 'TNB', 'WTC', 'AE', 'MT', 'VROS', 'CNY', 'DGD', 'HRP',
                'MCO', 'BITX', 'SNT', 'THETA', 'GNT'}, 'OMG': {'ETH', 'USD', 'KCASH', 'CNY'},
        'IOST': {'ETH', 'KCASH', 'DT'}, 'ZIL': {'ETH', 'USD', 'KCASH', 'CNY'}, 'ELF': {'ETH', 'KCASH'},
        'TNB': {'ETH', 'KCASH'}, 'ADX': {'ETH', 'KCASH'}, 'DGD': {'ETH', 'KCASH'},
        'ZRX': {'ETH', 'USD', 'KCASH', 'CNY'}, 'ENG': {'ETH', 'KCASH'}, 'THETA': {'ETH', 'USD', 'KCASH', 'CNY'},
        'MANA': {'ETH', 'KCASH'}, 'APPC': {'ETH', 'KCASH'}, 'BLZ': {'ETH', 'KCASH'}, 'MCO': {'ETH', 'KCASH'},
        'CMT': {'ETH', 'BWL', 'KCASH', 'DT'}, 'BNB': {'ETH', 'USD', 'KCASH', 'CNY'}, 'AE': {'ETH', 'KCASH'},
        'BTM': {'ETH', 'KCASH'}, 'BAT': {'ETH', 'USD', 'KCASH', 'CNY'}, 'GNT': {'ETH', 'KCASH'},
        'WTC': {'ETH', 'KCASH'}, 'SNT': {'ETH', 'KCASH'}, 'KEX': {'ETH', 'KCASH'}, 'WISH': {'KCASH'}, 'KICK': {'SUB'},
        'SUB': {'KICK'}, 'BITX': {'ETH'}, 'GUSD': {'ETH'}, 'MT': {'ETH'}, 'HRP': {'ETH'}, 'DT': {'IOST', 'CMT'},
        'BWL': {'ETH', 'CMT'}, 'VROS': {'ETH', 'KCASH'}, 'ONOT': {'ETH', 'KCASH'},
        'CNY': {'ZRX', 'OMG', 'BNB', 'ETH', 'THETA', 'BAT', 'ZIL'},
        'USD': {'ZRX', 'OMG', 'BNB', 'ETH', 'THETA', 'BAT', 'ZIL'}}
    # graph = {'MCO': {'ETH'},
    #          'ETH': {'BTM', 'KCASH', 'IOST', 'AE', 'GNT', 'THETA', 'USD', 'BLZ', 'MANA', 'ELF', 'TNB', 'ENG', 'MT',
    #                  'OMG', 'ZRX', 'CMT', 'WTC', 'CNY', 'MCO', 'APPC', 'ZIL', 'ADX', 'DGD', 'BAT'}, 'DGD': {'ETH'},
    #          'ZRX': {'ETH', 'CNY', 'USD'}, 'BTM': {'ETH'}, 'OMG': {'ETH', 'CNY', 'USD'}, 'MT': {'ETH'},
    #          'KCASH': {'ETH'}, 'MANA': {'ETH'}, 'ELF': {'ETH'}, 'ZIL': {'ETH', 'CNY', 'USD'}, 'CMT': {'ETH'},
    #          'THETA': {'ETH', 'CNY', 'USD'}, 'GNT': {'ETH'}, 'AE': {'ETH'}, 'BLZ': {'ETH'}, 'ADX': {'ETH'},
    #          'TNB': {'ETH'}, 'IOST': {'ETH'}, 'APPC': {'ETH'}, 'WTC': {'ETH'}, 'BAT': {'ETH', 'CNY', 'USD'},
    #          'ENG': {'ETH'}, 'CNY': {'ETH', 'OMG', 'ZRX', 'ZIL', 'THETA', 'BAT'},
    #          'USD': {'ETH', 'OMG', 'ZRX', 'ZIL', 'THETA', 'BAT'}}

    # 测试
    path = search(graph, "MT", "CNY")
    print(path)
    # s(graph, "ADX", "USD")
    #
    price = cal_price("bytetrade", path)
    print(price)
