import ecdsa
import binascii
import random

class Wallet:
      def __init__(self):
        self.private_key = self.generate_private_key()
        self.public_key = self.generate_public_key()
        self.balance = 0  # Ödül için bir bakiye

      def generate_private_key(self):
            private_key = ecdsa.SigningKey.generate(curve=ecdsa.SECP256k1)
            return binascii.hexlify(private_key.to_string()).decode('utf-8')

      def generate_public_key(self):
            private_key_bytes = binascii.unhexlify(self.private_key)
            sk = ecdsa.SigningKey.from_string(private_key_bytes, curve=ecdsa.SECP256k1)
            vk = sk.get_verifying_key()
            return binascii.hexlify(vk.to_string()).decode('utf-8')
            