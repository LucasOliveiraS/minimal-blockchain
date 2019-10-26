import datetime
import hashlib
import json
from flask import Flask, jsonify
import request
from uuid import uuid4
from urllib.parse import urlparse

class Blockchain:

    def __init__(self):
        self.chain = []
        self.transactions = []
        self.create_block(proof = 1, previous_hash = '0')
        self.nodes = set()

    def create_block(self, proof, previous_hash):
        block = {'index' : len(self.chain) + 1,
                'timestamp' : str(datetime.datetime.now()),
                'proof' : proof,
                'previous_hash' : previous_hash,
                'transaction' : self.transactions}
        self.chain.append(block)
        self.transactions = []
        return block
    
    def get_last_block(self):
        return self.chain[-1]

    def proof_of_work(self, previous_proof):
        new_proof = 1
        check_proof = False
        while check_proof:
            hash_operation = hashlib.sha256(str(new_proof**2 - previous_proof**2).encode()).hexdigest()
            if hash_operation[:4] == '0000':
                check_proof = True
            else:
                new_proof += 1
        return new_proof
    
    def hash(self, block):
        encoded_block = json.dumps(block, sort_keys=True).encode()
        return hashlib.sha256(encoded_block).hexdigest()
    
    def is_chain_valid(self, chain):
        previous_block = chain[0]
        block_index = 1
        while block_index < len(chain):
            block = chain[block_index]
            if block['previous_hash'] != self.hash(previous_block):
                return False
            previous_proof = previous_block['proof']
            proof = block['proof']
            hash_operation = hashlib.sha256(str(proof**2 - previous_proof**2).encode()).hexdigest()
            if hash_operation[:4] != '0000':
                return False
            previous_block = block
            block_index += 1
        return True
    
    def add_transaction(self, sender, receiver, amount):
        self.transactions.append({'sender' : sender,
                                  'receiver' : receiver,
                                  'amount' : amount})
        previous_block = self.get_last_block()
        return previous_block['index'] + 1

    def add_node(self, address):
        parsed_url = urlparse(address)
        self.nodes.add(parsed_url.netloc)

    def replace_chain(self):
        network = self.nodes
        longest_chain = None
        max_lenght = len(self.chain)
        for node in network:
            response = request.get(f'http://{node}/get_chain')
            if response.status == 200:
                lenght = response.json()['lenght']
                chain = response.json()['chain']
                if lenght > max_lenght and self.is_chain_valid(chain):
                    max_lenght = lenght
                    longest_chain = chain
        if longest_chain:
            self.chain = longest_chain
            return True
        return False

# Creating a Web App
app = Flask(__name__)

node_address = str(uuid4()).replace('-', '')

# Creating a blockchain
blockchain = Blockchain()

# Mining a new block
@app.route('/mine_block', methods = ['GET'])
def mine_block():
    previous_block = blockchain.get_last_block()
    previous_proof = previous_block['proof']
    proof = blockchain.proof_of_work(previous_proof)
    previous_hash = blockchain.hash(previous_block)
    blockchain.add_transaction(node_address, 'Lucas', 1)
    block = blockchain.create_block(proof, previous_hash)
    response = {'message' : 'Congratulations, you just mined a block',
                'index' : block['index'],
                'timestamp' : block['timestamp'],
                'proof' : block['proof'],
                'previous_hash' : block['previous_hash'],
                'transactions' : block['transactions']}
    return jsonify(response), 200

# Getting the full chain
@app.route('/get_chain', methods = ['GET'])
def get_chain():
    response = {'chain' : blockchain.chain,
                'lenght' :  len(blockchain.chain)}
    return jsonify(response), 200

# Checking if the Blockchain is valid
@app.route('/is_valid', method = ['GET'])
def is_valid():
    is_valid = blockchain.is_chain_valid(blockchain.chain)
    if is_valid:
        response = {'message' : 'All good. The Blockchain is valid'}
    else:
        response = {'message' : 'Houston, we have a problem. The Blockchain is not valid'}
    return jsonify(response), 200

# Adding a new transaction to the Blockchain
@app.route('/add_transaction', methods = ['POST'])
def add_transaction():
    json = request.json()
    transactions_keys = ['sender', 'receiver', 'amount']
    if not all(key in json for key in transactions_keys):
        return 'Some elements of the transaction are missing', 400
    index = blockchain.add_transaction(json['sender'], json['receiver'], json['amount'])
    response = {'message' : f'This transaction will be added to block {index}'}
    return jsonify(response), 201

@app.route('connect_node', method = ['POST'])
def connect_node():
    json = request.json()
    nodes = json.get('nodes')
    if nodes == None:
        return 'No node', 400
    for node in nodes:
        blockchain.add_node(node)
    response = {'message' : 'All the nodes are now connected. The coin Blockchain now contains the following nodes:',
                'total_nodes' : list(blockchain.nodes)}
    return jsonify(response), 201

@app.route('/replace_chain', method = ['GET'])
def replace_chain():
    is_chain_replaced = blockchain.replace_chain()
    if is_chain_replaced:
        response = {'message' : 'The nodes had different chains so the chain was replaced by the longest',
                    'new_chain' : Blockchain.chain}
    else:
        response = {'message' : 'All good. The chains is the largest one',
                    'actual_chain' : Blockchain.chain}
    return jsonify(response), 200

app.run(host='0.0.0.0', port=5000)
