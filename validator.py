import ecdsa
import binascii
import random

class Validator:
      def __init__(self, private_key, port, stake = random.randint(30, 100)):
        self.stake = stake
        self.public_key = self.generate_public_key(private_key)
        self.port = port
        self.vote = 0
        self.balance = 0  # Ödül için bir bakiye
        
      def to_dict(self):
            return {'public_key': self.public_key, 'port': self.port, 'stake': self.stake, 'vote': self.vote, 'balance': self.balance}

      def generate_public_key(self, private_key):
            private_key_bytes = binascii.unhexlify(private_key)
            sk = ecdsa.SigningKey.from_string(private_key_bytes, curve=ecdsa.SECP256k1)
            vk = sk.get_verifying_key()
            return binascii.hexlify(vk.to_string()).decode('utf-8')

      def receive_reward(self, amount):
            self.balance += amount
            
      def clear_vote(self):
            self.vote = 0
            return self.vote