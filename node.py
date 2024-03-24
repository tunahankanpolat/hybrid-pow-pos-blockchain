from flask import Flask, jsonify, request
from blockchain import Blockchain
from validator import Validator
import http.client
import json
import random
import ecdsa
import binascii
import os

app = Flask(__name__)
blockchain = Blockchain()
validators = []
port =  os.getenv('PORT')
total_node = int(os.getenv('TOTAL_NODE'))
start_node = int(os.getenv('START_NODE'))
select_validators_size = int(os.getenv('SELECT_VALIDATORS_SIZE'))

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
            validators[index].vote += 1
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
      validator = generate_validator(generate_private_key(), port)
      validators.append(validator)
      body = {'private_key': validator.public_key}
      broadcast_to_nodes('POST', '/broad_cast_add_validator', body)
      
@app.route('/broad_cast_add_validator', methods=['POST'])
def broad_cast_add_validator():
      validator = request.get_json()
      validators.append(validator)
      return jsonify({'message': 'Validator added'}), 201

@app.route('/mine_block', methods=['GET'])
def mine_block():
	previous_block = blockchain.print_previous_block()
	previous_proof = previous_block['proof']
	proof = blockchain.proof_of_work(previous_proof)
	previous_hash = blockchain.calculate_hash(previous_block)
	block = blockchain.create_block(proof, previous_hash)

	response = {'message': 'A block is MINED',
				'index': block['index'],
				'timestamp': block['timestamp'],
				'proof': block['proof'],
				'previous_hash': block['previous_hash']}

	return jsonify(response), 200

# Display blockchain in json format
@app.route('/get_chain', methods=['GET'])
def display_chain():
      print(blockchain.chain)
      chain = [block.to_dict() for block in blockchain.chain]
      response = {'chain': chain,
				'length': len(blockchain.chain)}
      print("response", response)
      return jsonify(response), 200

# Check validity of blockchain


@app.route('/valid', methods=['GET'])
def valid():
	valid = blockchain.chain_valid(blockchain.chain)

	if valid:
		response = {'message': 'The Blockchain is valid.'}
	else:
		response = {'message': 'The Blockchain is not valid.'}
	return jsonify(response), 200
            
       
@app.route('/add_transaction', methods=['POST'])
def add_transaction():
      data = request.get_json()
      required_fields = ['sender', 'receiver', 'amount', 'signature']
      boolean = check_required_fields(data, required_fields)
      if boolean:
            sender = data['sender']
            receiver = data['receiver']
            amount = data['amount']
            signature = data['signature']

            # İmzayı doğrula
            public_key = ecdsa.VerifyingKey.from_string(binascii.unhexlify(sender), curve=ecdsa.SECP256k1)
            try:
                  public_key.verify(binascii.unhexlify(signature), f'{sender}{receiver}{amount}'.encode())
            except ecdsa.BadSignatureError:
                  return jsonify({'message': 'Invalid signature'}), 400

            blockchain.add_transaction("POST", "/broadcast_transaction", data)
            
            if blockchain.is_pool_full():
                  select_validators()
            return jsonify({'message': 'Transaction added to the pool'}), 201
  
@app.route('/get_balance/<public_key>', methods=['GET'])
def get_balance(public_key):
    balance = 0
    for block in blockchain.chain:
        for transaction in block.transactions:
            if transaction['sender'] == public_key:
                balance -= transaction['amount']
            if transaction['receiver'] == public_key:
                balance += transaction['amount']
    return jsonify({'balance': balance}), 200
	
 
 
 

async def create_block():
      previous_block = blockchain.print_previous_block()
      previous_hash = previous_block['hash']
      blockchain.create_block(blockchain.transaction_pool.transactions, previous_hash)
      blockchain.transaction_pool.clear()      
      
      
def broadcast_to_nodes(method, path, data=None):
      for i in range(total_node):
            if i != start_node:
                  conn = http.client.HTTPConnection(f'localhost:{start_node + i}')
                  headers = None
                  if method == 'POST' and data is not None:
                        data = json.dumps(data)
                        headers = {'Content-type': 'application/json'}
                  conn.request(method, path, data, headers)	
                  
async def broadcast_to_nodes_async(method, path, data=None):
      responses = []
      for i in range(total_node):
            if i != start_node:
                  conn = http.client.HTTPConnection(f'localhost:{start_node + i}')
                  headers = None
                  if method == 'POST' and data is not None:
                        data = json.dumps(data)
                        headers = {'Content-type': 'application/json'}
                  await conn.request(method, path, data, headers)	
                  response = conn.getresponse()
                  responses.append(response.read())
      return responses
                  

def check_required_fields(data, required_fields):
      for field in required_fields:
            if not data.get(field):
                  response = {'message': f'{field} is required'}
                  return jsonify(response), 400
      return True

async def broadcast_select_validators():
      validator_indexes = select_validator_indexes(validators, blockchain.total_stake, select_validators_size)
      increase_validator_vote(validator_indexes)
      body = {'validator_indexes': validator_indexes}
      responses = await broadcast_to_nodes_async('POST', '/broadcast_select_validators', body)
      for validator_indexes in responses:
            increase_validator_vote(validator_indexes)
      
      selected_validators = select_validators()
      ###TODO: Broadcast selected validators to all nodes
            

def select_validators(validators):
      validators.sort(key=lambda x: x.vote, reverse=True)
      selected_validators = validators[:select_validators_size]
      return selected_validators
      

###BROADCASTS

@app.route('/broadcast_select_validators', methods=['POST'])
def select_validators():
      data = request.get_json()
      required_fields = ['validator_indexes']
      boolean = check_required_fields(data, required_fields)
      if boolean:
            validator_indexes = data['validator_indexes']
            increase_validator_vote(validator_indexes)
            validator_indexes = select_validator_indexes(validators, blockchain.total_stake, select_validators_size)
            increase_validator_vote(validator_indexes)
            body = {'validator_indexes': validator_indexes}
            return jsonify(body), 201


@app.route('/broadcast_transaction', methods=['POST'])
def broadcast_transaction():
      data = request.get_json()
      required_fields = ['sender', 'receiver', 'amount', 'signature']
      boolean = check_required_fields(data, required_fields)
      if boolean:
            sender = data['sender']
            receiver = data['receiver']
            amount = data['amount']
            signature = data['signature']

            # İmzayı doğrula
            public_key = ecdsa.VerifyingKey.from_string(binascii.unhexlify(sender), curve=ecdsa.SECP256k1)
            try:
                  public_key.verify(binascii.unhexlify(signature), f'{sender}{receiver}{amount}'.encode())
            except ecdsa.BadSignatureError:
                  return jsonify({'message': 'Invalid signature'}), 400

            blockchain.add_transaction(data)
            
            if blockchain.is_pool_full():
                  create_block()
            return jsonify({'message': 'Transaction added to the pool'}), 201

app.run(host='127.0.0.1', port=port)