from flask import Flask, jsonify, request
from transaction import Transaction
from blockchain import Blockchain
import http.client
import ecdsa
import binascii
import json

app = Flask(__name__)

# Add a transaction to the pool
NODE_ADDRESS = 'http://localhost:5001'


@app.route('/add_transaction', methods=['POST'])
async def add_transaction(private_key):
      sender_private_key = request.json['private_key']
      receiver = request.json['receiver']
      amount = request.json['amount']
      sender_public_key = convert_private_key_to_public_key(sender_private_key)
      transaction_message = f'{sender_public_key}{receiver}{amount}'
      signature = sign_transaction(sender_private_key, transaction_message)

      conn = http.client.HTTPConnection(NODE_ADDRESS[7:])
      headers = {'Content-type': 'application/json'}
      transaction_data = json.dumps({'sender': sender_public_key, 'receiver': receiver, 'amount': amount, 'signature': signature})
      conn.request('POST', '/add_transaction', transaction_data, headers)
      response = conn.getresponse()
      return response.read()


@app.route('/get_balance/<public_key>', methods=['GET'])
def get_balance(public_key):
    conn = http.client.HTTPConnection(NODE_ADDRESS[7:])
    conn.request('GET', f'/get_balance/{public_key}')
    response = conn.getresponse()
    return response.read()

def convert_private_key_to_public_key(private_key):
    private_key_bytes = binascii.unhexlify(private_key)
    sk = ecdsa.SigningKey.from_string(private_key_bytes, curve=ecdsa.SECP256k1)
    vk = sk.get_verifying_key()
    public_key = binascii.hexlify(vk.to_string()).decode('utf-8')
    return public_key

def sign_transaction(private_key, message):
    private_key_bytes = binascii.unhexlify(private_key)
    sk = ecdsa.SigningKey.from_string(private_key_bytes, curve=ecdsa.SECP256k1)
    signature = sk.sign(message.encode())
    return binascii.hexlify(signature).decode('utf-8')