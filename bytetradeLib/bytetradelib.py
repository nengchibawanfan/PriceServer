import os

curDir = os.path.dirname(__file__)

class bytetradelib():

    def get_address_from_wif_private_key(self, private_key):
        pass

    def get_publickey_from_wif_private_key(self, private_key):
        pass

    def get_order_id_from_tx_id(self, tx_id_str, op_id):
        pass

    def create_order_transaction(self,fee,creator,side,order_type,market_name,amount,price,use_btt_as_fee,freeze_btt_fee,dapp,private_key):
        pass

    def create_order3_transaction(self,fee,creator,side,order_type,market_name,amount,price,use_btt_as_fee,freeze_btt_fee,custom_btt_fee_rate,custom_no_btt_fee_rate,money_id,stock_id,dapp,private_key):
        pass

    def cancel_order_transaction(self,fee,creator,market_name,order_id,dapp,private_key):
         pass

    def cancel_order2_transaction(self,fee,creator,market_name,order_id,money_id,stock_id,dapp,private_key):
         pass

    def transfer_order_transaction(self,fee,from_id,to_id,asset_type,amount,dapp,private_key):
        pass


    def transfer2_order_transaction(self,fee,from_id,to_id,asset_type,amount,dapp,message,private_key):
        pass


    def propose_withdraw_transaction(self,fee,from_id,to_external_address,asset_type,amount,dapp,private_key):
        pass

