# -*- coding: utf-8 -*-
# Author: zhangchao
# Date: 
# Desc: 性能测试例子
import random

from locust import HttpLocust, TaskSet, task

class UserBehavior(TaskSet):

    @task(1)
    def graphql(self):
        lst = ['''{
  symbols(symbolName: "CMT/ETH, MT/ETH, KCASH/ETH, MT/BTC, CMT/BTC, APPC/ETH, BAT/ETH", currency: "CNY, USD, KRW"){
    symbolName
    price{
      currency
      price
    }
  }
}''', '''{
  symbols(symbolName: "MT/ETH, CMT/ETH", currency: "USD"){
    symbolName
    price{
      currency
      price
    }
  }
}''', '''{
  symbols(symbolName: "KCASH, MT", currency: "USD, CNY"){
    symbolName
    price{
      currency
      price
    }
  }
}''', '''{
  symbols(symbolName: "CMT", currency: "CNY"){
    symbolName
    price{
      currency
      price
    }
  }
}''' ,
               '''{
  symbols{
    symbolName
    price{
      currency
      price
    }
  }
}'''
               ]
        # param = random.choices(lst)
        param = lst[-1]

        params = {'query': param}

        self.client.post("/graphql", params=params)
        # assert r.state_code == 200


class WebsiteUser(HttpLocust):
    # host = "http://18.179.204.45:5000"
    task_set = UserBehavior
    min_wait = 5000
    max_wait = 9000

if __name__ == '__main__':
    # locust -f performance_test.py --host=http://18.179.204.45:5000
    pass