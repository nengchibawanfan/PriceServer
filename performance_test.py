from locust import HttpLocust, TaskSet, task

from gql import Client, gql
from gql.transport.requests import RequestsHTTPTransport


class MyTaskSet(TaskSet):


    @task(1)
    def graphql(self):
        query = gql('''
        {
          priceServer{
            info {
              exchangeName
              coinList {
                symbolName
                price {
                  currency
                  price
                }
              }
            }
          }
        }
            ''')
        # self.client1.execute(query)
        res = self.client.execute(query)
        print(res)


class MyLocust(HttpLocust):
    task_set = MyTaskSet
    min_wait = 5000
    max_wait = 15000

