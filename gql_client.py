import mock

from gql import Client, gql
from gql.transport.requests import RequestsHTTPTransport



client = Client(
        transport=RequestsHTTPTransport(url='http://18.179.204.45:5000/graphql')
    )

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

res = client.execute(query)

print(res)