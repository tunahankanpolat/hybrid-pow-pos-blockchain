from time import time
import json
import hashlib

class Block:
      def __init__(self, index, transactions, previous_hash, nonce=0, timestamp = time()):
        self.index = index
        self.transactions = transactions
        self.timestamp = timestamp
        self.previous_hash = previous_hash
        self.nonce = nonce
        self.hash = self.calculate_hash()

      def calculate_hash(self):
            block_string = json.dumps(self.__dict__, sort_keys=True)
            return hashlib.sha256(block_string.encode()).hexdigest()
      
      def to_dict(self):
            return {
                  'index': self.index,
                  'transactions': self.transactions,
                  'timestamp': self.timestamp,
                  'previous_hash': self.previous_hash,
                  'nonce': self.nonce,
                  'hash': self.hash
            }
      
      @staticmethod
      def genesis_block():
            return Block(0, [], '0')
