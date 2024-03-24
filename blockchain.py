import datetime
import hashlib
import json
from block import Block
from transaction import Transaction
from transaction_pool import TransactionPool
from validator import Validator
from dotenv import load_dotenv
import os
import random

load_dotenv()

class Blockchain:
      def __init__(self):
            self.chain = [Block.genesis_block()]
            self.total_stake = 0
            self.transaction_pool = TransactionPool()
            self.block_size = int(os.getenv('BLOCK_SIZE'))
      
      def add_transaction(self, sender, receiver, amount):
            transaction = Transaction(sender, receiver, amount).to_dict()
            self.transaction_pool.add_transaction(transaction)
            return transaction
      
      def is_pool_full(self):
            return len(self.transaction_pool.transactions) >= self.block_size
      
      def create_block(self, transactions, previous_hash):
            block = Block(len(self.chain) + 1, transactions, previous_hash).to_dict()
            self.chain.append(block)
            return block
      
      def print_previous_block(self):
            return self.chain[-1]

      def proof_of_work(self, previous_proof):
            new_proof = 1
            check_proof = False

            while check_proof is False:
                  hash_operation = hashlib.sha256(
                        str(new_proof**2 - previous_proof**2).encode()).hexdigest()
                  if hash_operation[:5] == '00000':
                        check_proof = True
                  else:
                        new_proof += 1

            return new_proof

      def calculate_hash(self, block):
            encoded_block = json.dumps(block, sort_keys=True)
            return hashlib.sha256(encoded_block.encode()).hexdigest()
      

      def chain_valid(self, chain):
            previous_block = chain[0]
            block_index = 1

            while block_index < len(chain):
                  block = chain[block_index]
                  if block['previous_hash'] != self.calculate_hash(previous_block):
                        return False

                  previous_proof = previous_block['proof']
                  proof = block['proof']
                  hash_operation = hashlib.sha256(
                        str(proof**2 - previous_proof**2).encode()).hexdigest()

                  if hash_operation[:5] != '00000':
                        return False
                  previous_block = block
                  block_index += 1

            return True
