from flask import Flask, jsonify, request
from blockchain import Blockchain
from validator import Validator
from threading import Thread
import http.client
import json
import random
import ecdsa
import aiohttp
import asyncio
import binascii
import os

app = Flask(__name__)
blockchain = Blockchain()
validators = []
port =  int(os.getenv('PORT'))
total_node = int(os.getenv('TOTAL_NODE'))
start_node = int(os.getenv('START_NODE'))
selected_validators_size = int(os.getenv('SELECTED_VALIDATOR_SIZE'))
create_block_thread_running = False

def select_validator_indexes(validators, total_stake, required_validators=3):
      selected_validators_index = []
      remaining_validators = validators[:]
      remaining_weights = [(int(validator["stake"]) / total_stake) for validator in remaining_validators]
      
      for _ in range(required_validators):
            selected_validator = random.choices(remaining_validators, weights=remaining_weights, k=1)[0]
            selected_index = remaining_validators.index(selected_validator)
            selected_validators_index.append(selected_index)
            remaining_validators.pop(selected_index)
            remaining_weights.pop(selected_index)
            remaining_weights = [weight / sum(remaining_weights) for weight in remaining_weights]  # Normalize weights

      return selected_validators_index

def increase_validator_vote(validators, validator_indexes):
      for index in validator_indexes:
            print("Validator: ", validators[int(index)])
            validators[index]['vote'] += 1
      return validators

def generate_private_key():
      private_key = ecdsa.SigningKey.generate(curve=ecdsa.SECP256k1)
      return binascii.hexlify(private_key.to_string()).decode('utf-8')

def generate_validator(private_key, port):
      validator = Validator(private_key, port)
      blockchain.total_stake += validator.stake
      return validator

@app.route('/add_validator', methods=['POST'])
async def add_validator():
      validator = generate_validator(generate_private_key(), port).to_dict()
      validators.append(validator)
      print("Validator added: ", validator)
      broadcast_to_nodes('POST', '/broad_cast_add_validator', validator)
      return jsonify({'message': 'Validator added'}), 201
      
@app.route('/broad_cast_add_validator', methods=['POST'])
def broad_cast_add_validator():
      validator = request.get_json()
      validators.append(validator)
      blockchain.total_stake += int(validator['stake'])
      print("Validator added: ", validator)
      return jsonify({'message': 'Validator added'}), 201

# Display blockchain in json format
@app.route('/get_chain', methods=['GET'])
def display_chain():
      print("Blockchain: ", blockchain.chain)
      response = {'chain': blockchain.chain,
				'length': len(blockchain.chain)}
      print("response", response)
      return jsonify(response), 200

# Broadcast genesis block to all nodes
@app.route('/broadcast_genesis_block', methods=['POST'])
def broadcast_genesis_block():
      genesis_block = blockchain.generate_genesis_block()
      validators.clear()
      body = {'genesis_block': genesis_block}
      print("genesis_block", genesis_block)
      print("body", body)
      broadcast_to_nodes('POST', '/create_genesis_block', body)
      return jsonify({'message': 'Genesis block broadcasted'}), 201

@app.route('/create_genesis_block', methods=['POST'])
def create_genesis_block():
      data = request.get_json()
      print("data", data)
      validators.clear()
      required_fields = ['genesis_block']
      boolean = check_required_fields(data, required_fields)
      if boolean:
            genesis_block = data['genesis_block']
            blockchain.add_genesis_block(genesis_block)
            return jsonify({'message': 'Genesis block added'}), 201
      
# Get transaction pool
@app.route('/get_transaction_pool', methods=['GET'])
def get_transaction_pool():
      response = {'transactions': blockchain.transaction_pool.to_dict()}
      return jsonify(response), 200
       
@app.route('/add_transaction', methods=['POST'])
def add_transaction():
      data = request.get_json()
      print("data", data)
      required_fields = ['sender', 'recipient', 'amount', 'signature']
      boolean = check_required_fields(data, required_fields)
      if boolean:
            sender = data['sender']
            recipient = data['recipient']
            amount = data['amount']
            signature = data['signature']
            print("Transaction Data: ", data)
            # İmzayı doğrula
            try:
                  public_key = ecdsa.VerifyingKey.from_string(binascii.unhexlify(sender), curve=ecdsa.SECP256k1)
                  public_key.verify(binascii.unhexlify(signature), f'{sender}{recipient}{amount}'.encode())
            except ecdsa.BadSignatureError:
                  return jsonify({'message': 'Invalid signature'}), 400
            except ecdsa.BadDigestError:
                  return jsonify({'message': 'Invalid digest'}), 400
            except Exception:
                  return jsonify({'message': 'Invalid point'}), 400
                  

            transaction = blockchain.add_transaction(sender, recipient, amount)
            transaction['signature'] = signature
            # Broadcast transaction to all nodes
            broadcast_to_nodes('POST', '/broadcast_transaction', transaction)
            if blockchain.is_pool_full():
                  global create_block_thread_running
                  create_block_thread_running = True
                  Thread(target=create_block_thread).start()
            return jsonify({'message': 'Transaction added to the pool'}), 201
  
@app.route('/get_balance/<public_key>', methods=['GET'])
def get_balance(public_key):
    balance = 0
    for block in blockchain.chain:
        for transaction in block["transactions"]:
            if transaction["sender"] == public_key:
                balance -= float(transaction["amount"])
            if transaction["recipient"] == public_key:
                balance += float(transaction["amount"])
    return jsonify({'balance': balance}), 200
 
 
def create_block_thread():
      global create_block_thread_running
      print("...create_block_thread...")
      print("Create block thread running: ", create_block_thread_running)
      loop = asyncio.new_event_loop()
      asyncio.set_event_loop(loop)
      try:
            loop.run_until_complete(create_block())
      finally:
            loop.close()


async def create_block():
      selected_validators = await broadcast_select_validators()
      print("Selected validators: ", selected_validators)
      headers = {'Content-type': 'application/json'}
      for validator in selected_validators:
            print("Validator: ", validator)
            conn = http.client.HTTPConnection(f'localhost:{validator["port"]}')
            conn.request('POST', '/create_block', json.dumps({'selected_validators': selected_validators}).encode('utf-8'), headers)
            conn.close()
          
      

def broadcast_to_nodes(method, path, data=None):
      print("Broadcast to nodes")
      print("Method: ", method)
      print("Path: ", path)
      print("Data: ", data)
      data = json.dumps(data)
      print("port: ", port)
      for i in range(total_node):
            if start_node + i != port:
                  print("Broadcast to ", start_node + i)
                  conn = http.client.HTTPConnection(f'localhost:{start_node + i}')
                  headers = None
                  if method == 'POST' and data is not None:
                        headers = {'Content-type': 'application/json'}
                        conn.request(method, path, data, headers)	
                  else:
                        conn.request(method, path)
                  conn.close()

                  
# def broadcast_to_nodes_async(method, path, data=None):
#       data = json.dumps(data)
#       responses = []
#       for i in range(total_node):
#             if start_node + i != port:
#                   print("Broadcast to ", start_node + i)
#                   conn = http.client.HTTPConnection(f'localhost:{start_node + i}')
#                   headers = None
#                   if method == 'POST' and data is not None:
#                         headers = {'Content-type': 'application/json'}
#                         conn.request(method, path, data, headers)	
#                   else:
#                         conn.request(method, path)
#                   response = conn.getresponse()
#                   responses.append(response.read())
#                   conn.close()
#       return responses

async def broadcast_to_nodes_async(method, path, data=None):
      data = json.dumps(data)
      responses = []
      async with aiohttp.ClientSession() as session:
            tasks = []
            for i in range(total_node):
                  if start_node + i != port:
                        url = f'http://localhost:{start_node + i}{path}'
                        if method == 'POST' and data is not None:
                              print("POST Broadcast to http://localhost:", str(start_node + i) + "/" + path)
                              headers = {'Content-type': 'application/json'}
                              tasks.append(session.post(url, data=data, headers=headers))
                        else:
                              print("GET Broadcast to http://localhost:", str(start_node + i) + "/" + path)
                              tasks.append(session.get(url))
            responses = await asyncio.gather(*tasks)
      return [await response.text() for response in responses]
                  

def check_required_fields(data, required_fields):
      for field in required_fields:
            if not data.get(field):
                  response = {'message': f'{field} is required'}
                  return jsonify(response), 400
      return True

async def broadcast_select_validators():
      validator_indexes = select_validator_indexes(validators, blockchain.total_stake, selected_validators_size)
      increase_validator_vote(validators, validator_indexes)
      print("Selected validators: ", validator_indexes)
      responses = await broadcast_to_nodes_async('GET', '/broadcast_select_validators')
      responses = [json.loads(response) for response in responses]
      print("Responses: ", responses)
      for validator_indexes in responses:
            print("Validator indexes: ", validator_indexes["validator_indexes"])
            increase_validator_vote(validators,  validator_indexes["validator_indexes"])
      
      selected_validators = select_validators(validators)
      print("Winner validators: ", selected_validators)
      return selected_validators
            

def select_validators(validators):
      validators.sort(key=lambda x: x["vote"], reverse=True)
      selected_validators = validators[:selected_validators_size]
      return selected_validators

# Select validators
@app.route('/select_validators', methods=['GET'])
async def get_select_validators():
      selected_validators = await broadcast_select_validators()
      return jsonify({'selected_validators': selected_validators}), 200
    
# Write a endpoint for get stake of port
@app.route('/get_stake', methods=['GET'])
def get_stake():
      return jsonify({'stake': blockchain.total_stake}), 200

@app.route('/get_validators', methods=['GET'])
def get_validators():
      return jsonify({'validators': validators}), 200

###BROADCASTS
@app.route('/create_block', methods=['POST'])
async def get_create_block():
      selected_validators = request.get_json()
      blockchain.create_block_thread_running = True
      block = await blockchain.create_block(blockchain.transaction_pool.transactions)
      if block:
            blockchain.transaction_pool.clear()
            # Broadcast block to all nodes for clear transaction pool
            broadcast_to_selected_validators_for_stop_create_block(selected_validators['selected_validators'])
            broadcast_to_nodes('GET', '/clear_transaction_pool_and_vote')
            broadcast_to_nodes('POST', '/broadcast_add_block', block)
            return jsonify({'message': 'Block created'}), 201
      else:
            return jsonify({'message': 'Block not created'}), 400

def broadcast_to_selected_validators_for_stop_create_block(selected_validators):
      for validator in selected_validators:
            if validator["port"] != port:
                  conn = http.client.HTTPConnection(f'localhost:{validator["port"]}')
                  conn.request('GET', '/stop_create_block')
                  conn.close()
                  
@app.route('/stop_create_block', methods=['GET'])
def stop_create_block():
      global create_block_thread_running
      blockchain.create_block_thread_running = False
      create_block_thread_running = False
      return jsonify({'message': 'Create block thread stopped'}), 200


@app.route('/broadcast_add_block', methods=['POST'])
def broadcast_block():
      block = request.get_json()
      blockchain.chain.append(block)
      return jsonify({'message': 'Block added'}), 201

# Write a endpoint for clear transaction pool
@app.route('/clear_transaction_pool_and_vote', methods=['GET'])
def clear_transaction_pool_and_vote():
      blockchain.transaction_pool.clear()
      clear_validator_votes()
      return jsonify({'message': 'Transaction pool and votes cleared'}), 200

def clear_validator_votes():
      for validator in validators:
            validator['vote'] = 0

@app.route('/broadcast_select_validators', methods=['GET'])
def get_broadcast_select_validators():
      validator_indexes = select_validator_indexes(validators, blockchain.total_stake, selected_validators_size)
      body = {'validator_indexes': validator_indexes}
      print("Selected validators: ", validator_indexes)
      return jsonify(body), 201

@app.route('/broadcast_transaction', methods=['POST'])
def broadcast_transaction():
      data = request.get_json()
      required_fields = ['sender', 'recipient', 'amount', 'signature', 'timestamp', 'hash']
      boolean = check_required_fields(data, required_fields)
      if boolean:
            sender = data['sender']
            recipient = data['recipient']
            amount = data['amount']
            signature = data['signature']
            timestamp = data['timestamp']
            hash = data['hash']
            print("Transaction Data: ", data)
            # İmzayı doğrula
            try:
                  public_key = ecdsa.VerifyingKey.from_string(binascii.unhexlify(sender), curve=ecdsa.SECP256k1)
                  public_key.verify(binascii.unhexlify(signature), f'{sender}{recipient}{amount}'.encode())
            except ecdsa.BadSignatureError:
                  return jsonify({'message': 'Invalid signature'}), 400
            except ecdsa.BadDigestError:
                  return jsonify({'message': 'Invalid digest'}), 400
            except Exception:
                  return jsonify({'message': 'Invalid point'}), 400

            blockchain.add_transaction(sender, recipient, amount, timestamp, hash)
            return jsonify({'message': 'Transaction added to the pool'}), 201

if __name__ == '__main__':
      app.run(host='127.0.0.1', port=port)