from locust import HttpLocust, TaskSet, task

class UserBehavior(TaskSet):

    @task(1)
    def graphql(self):
        # params = {'query': '''{
        #   priceServer{
        #     info {
        #       exchangeName
        #       coinList {
        #         symbolName
        #         price {
        #           currency
        #           price
        #         }
        #       }
        #     }
        #   }
        # }'''}

        params = {'query': '''{
  priceServer(exchangeName: "bytetrade", currency: "CNY",  symbol: "CMT/ETH"){
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
}'''}

        self.client.post("/graphql", params=params)
        # assert r.state_code == 200


class WebsiteUser(HttpLocust):
    # host = "http://18.179.204.45:5000"
    task_set = UserBehavior
    min_wait = 5000
    max_wait = 9000

if __name__ == '__main__':
    pass