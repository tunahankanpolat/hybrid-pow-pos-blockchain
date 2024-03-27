import datetime
import hashlib
import json
from block import Block
from transaction import Transaction
from transaction_pool import TransactionPool
from validator import Validator
import time
from dotenv import load_dotenv
import os
import random

load_dotenv()

class Blockchain:
      def __init__(self):
            self.chain = []
            self.total_stake = 0
            self.transaction_pool = TransactionPool()
            self.block_size = int(os.getenv('BLOCK_SIZE'))
            self.difficulty = int(os.getenv('DIFFICULTY'))
            self.create_block_thread_running = False
            

      def add_transaction(self, sender, recipient, amount, timestamp = None, hash = None):
            transaction = None
            if timestamp and hash:
                  transaction = Transaction(sender, recipient, amount, timestamp, hash).to_dict()
            else:
                  transaction = Transaction(sender, recipient, amount).to_dict()
            self.transaction_pool.add_transaction(transaction)
            print("Transaction added to the pool: ", transaction)
            return transaction
      
      def is_pool_full(self):
            return len(self.transaction_pool.transactions) >= self.block_size
            
      # def create_block(self, transactions, previous_hash):
      #       block = Block(len(self.chain) + 1, transactions, previous_hash).to_dict()
      #       print("Block created: ", block)
      #       self.chain.append(block)
      #       return block
      
      def add_genesis_block(self, genesis_block):
            self.chain.append(genesis_block)
            print("Genesis block added: ", genesis_block)
            return genesis_block
            
      
      def generate_genesis_block(self):
            genesis_block = Block(1, [], '0').to_dict()
            self.chain = [genesis_block]
            self.transaction_pool.clear()
            print("Genesis block created: ", genesis_block)
            return genesis_block
      
      async def create_block(self, transactions):
            print("Creating block...")
            print("Transactions: ", transactions)
            print("Previous chain: ", self.chain[-1])
            block = Block(len(self.chain) + 1, transactions, self.chain[-1]['hash'], 0)
            nonce = await self.proof_of_work(block)
            if not nonce:
                  return None
            block.nonce = nonce
            block.hash = block.calculate_hash()
            self.chain.append(block.to_dict())
            print("Block created: ", block.to_dict())
            return block.to_dict()
      
      def get_previous_block(self):
            return self.chain[-1]

      async def proof_of_work(self, block:Block):
            print("Mining block...")
            block.nonce = 0
            computed_hash = block.calculate_hash()
            while not self.valid_proof(computed_hash):
                  print("Creating block thread running: ", self.create_block_thread_running)
                  if not self.create_block_thread_running:
                        return None
                  block.nonce += 1
                  computed_hash = block.calculate_hash()
                  print("Computed hash: ", computed_hash, "Nonce: ", block.nonce)
            return block.nonce

      def valid_proof(self, computed_hash):
            return computed_hash.startswith('0' * self.difficulty)
      

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
