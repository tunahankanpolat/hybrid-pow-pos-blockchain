from time import time
import json
import hashlib

class Block:
      def __init__(self, index, transactions, previous_hash, nonce=0):
        self.index = index
        self.transactions = transactions
        self.timestamp = time()
        self.previous_hash = previous_hash
        self.nonce = nonce
        self.hash = self.calculate_hash()

      def calculate_hash(self):
            block_string = json.dumps(self.__dict__, sort_keys=True)
            return hashlib.sha256(block_string.encode()).hexdigest()
      
      def to_dict(self):
            return str(self.__dict__)
      
      @staticmethod
      def genesis_block():
            return Block(0, [], '0')
