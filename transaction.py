import hashlib
import json
from time import time

class Transaction:
      def __init__(self, sender, recipient, amount, timestamp = time(), hash = None):
            self.sender = sender
            self.recipient = recipient
            self.amount = amount
            self.timestamp = timestamp
            if hash:
                  self.hash = hash
            else:
                  self.hash = self.calculate_hash()

      def calculate_hash(self):
            transaction_string = json.dumps(self.__dict__, sort_keys=True)
            return hashlib.sha256(transaction_string.encode()).hexdigest()
      
      def to_dict(self):
            return {
                  'sender': self.sender,
                  'recipient': self.recipient,
                  'amount': self.amount,
                  'timestamp': self.timestamp,
                  'hash': self.hash
            }