import hashlib
import json
from time import time

class Transaction:
      def __init__(self, sender, recipient, amount):
            self.sender = sender
            self.recipient = recipient
            self.amount = amount
            self.timestamp = time()
            self.hash = self.calculate_hash()

      def calculate_hash(self):
            transaction_string = json.dumps(self.__dict__, sort_keys=True)
            return hashlib.sha256(transaction_string.encode()).hexdigest()
      
      def to_dict(self):
            return str(self.__dict__)