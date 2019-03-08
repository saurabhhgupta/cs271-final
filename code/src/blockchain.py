# encoding=utf8

import hashlib
import string
import json

CHAIN_INIT_FILE = "init_chain.txt"

'''
General hash function that returns a HASHED string
'''
def hash(data):
	return hashlib.sha256(data.encode('utf-8')).hexdigest()

'''
txA and txB are two transactions where each transaction is a string in the format: ”A B amount” 
(which means A sends B an amount of 5). And there are exactly two transactions in each list of transactions(in each block).
'''
class Transaction(object):
	def __init__(self, source, destination, amount):
		self.amount = int(amount)
		self.source = str(source)
		self.destination = str(destination)

	def stringify(self):
		transaction = "{} {} {}".format(self.source, self.destination, self.amount)
		return transaction

	def __repr__(self):
		transaction = "{} {} {}".format(self.source, self.destination, self.amount)
		return transaction

	def __eq__(self, other):
		if self is other:
			return True
		else:
			if self.source != other.source:
				return False
			if self.destination != other.destination:
				return False
			if self.amount != other.amount:
				return False
			return True

class Header(object):
	'''txA and txB must be HASHED strings (SHA256).'''
	def __init__(self, current_term, prev_block_header, hash_tx_a, hash_tx_b):
		'''
		Current term represents the term being used in Raft.
		'''
		self.current_term = current_term

		'''
		Hheader (B − 1) is the SHA256 hash of the header of the previous block, 
		which is the SHA256 of the string concatenation of term(B - 1), Hheader(B−2), HlistOfTxs(B− 1), and the nonce.
		'''
		self.hash_prev_block_header = hash(prev_block_header)

		'''
		HlistOfTxs(B) uses the Merkel Tree data structure, 
		which is a SHA256 hash of the concatenation of two SHA256 hashes of two transactions.
		'''
		self.hash_list_of_txs = hash(hash_tx_a + hash_tx_b)

		'''
		The nonce is a random string such that: Taking the SHA256 of the concatenation of HListOfTxs(H(X)||H(Y)) of the current block 
		and the nonce would give a resulting hash value with the last character being a digit (0-2). 
		In order to do that you will create the nonce randomly. The length of the nonce is up to you. 
		If the calculated hash value does not end with a digit between 0 and 2 (i.e. 0, 1 or 2) as its last character, 
		you will have to try another nonce again. In other words, you need to create the nonce randomly until the 
		rightmost character of the resulting hash value is a digit between (0-2).
		'''
		self.nonce = None

	def calc_nonce(self):
		self.nonce = 0
		accept_digit = ['0','1','2']
		while hash(str(self.nonce) + self.hash_list_of_txs)[-1] not in accept_digit:
			self.nonce += 1

	def create_header_json(self):
		header = {"current_term": self.current_term, 
				"hash_prev_block_header": self.hash_prev_block_header,
				"hash_list_of_txs": self.hash_list_of_txs,
				"nonce": self.nonce}
		return json.dumps(header)

	'''
	Stringify
	'''
	def stringify(self):
		return "{},{},{},{}".format(self.current_term, self.hash_prev_block_header, self.hash_list_of_txs, self.nonce)
		# print "{},{},{},{}".format(self.current_term, self.hash_prev_block_header, self.hash_list_of_txs, self.nonce)	

	def __eq__(self, other):
		if self is other:
			return True
		else:
			if self.current_term != other.current_term:
				return False
			if self.hash_prev_block_header != other.hash_prev_block_header:
				return False
			if self.hash_list_of_txs != other.hash_list_of_txs:
				return False
			if self.nonce != other.nonce:
				return False
			return True

class Block(object):
	def __init__(self, transactions, header):
		self.transactions = transactions # list of two transactions
		self.header = header
	
	def create_block_json(self):
		block = {"header": self.header.create_header_json(),
				"transactions": self.transactions}
		return json.dumps(block)

	def __eq__(self, other):
		if self is other:
			return True
		else:
			if self.transactions[0] != other.transactions[0]:
				return False
			if self.transactions[1] != other.transactions[1]:
				return False
			if self.header != other.header:
				return False
			return True

class Chain(object):
	def __init__(self):
		self.chain = []

	'''
	Assumes \n delimiter for triplets
	Returns list of transactions
	'''
	def parse_init_file(self, file):
		transaction_list = []
		with open(file, 'r') as config_file:
			line = config_file.readline()
			while line:
				# line = line.strip('\n')
				source, destination, amount = line.split(' ')
				transaction = Transaction(source, destination, int(amount))
				transaction_list.append(transaction)
				line = config_file.readline()
		# print transaction_list
		return transaction_list

	'''
	Initializes the blockchain with the input transactions from the config file.
	'''
	def init_blockchain(self, input_transaction_list):
		tx_pair = []
		header = None
		for index, transaction in enumerate(input_transaction_list):
			tx_pair.append(transaction.stringify())
			if index % 2 == 1: # if it is the 2nd transaction in the pair
				# if index == 1:
				# 	hash_prev_header = 'NULL' 
				# else:
				# 	hash_prev_header = hash(header.stringify())
				# header = Header(0, hash_prev_header, hash(tx_pair[0]), hash(tx_pair[1]))
				# block = Block(tx_pair, header)
				# block.header.calc_nonce()
				# self.chain.append(block)
				# tx_pair = []
				self.add_block(0, tx_pair)

	# ! TODO: print block like structures in terminal as a visual "blockchain"
	def print_pretty_chain(self):
		# note, hash256 always returns a 64 character long string for hexdigest()
		# print self.chain
		pass
	
	def create_chain_json(self):
		return json.dumps({"block_{}".format(i): self.chain[i].create_block_json() for i in range(len(self.chain))})
	
	def print_chain_json(self):
		print(self.create_chain_json())

	def add_block(self, current_term, TxList):
		if len(self.chain) == 0:
			hash_prev_header = 'NULL'
		else:
			hash_prev_header = hash(self.chain[-1].header.stringify())
		new_header = Header(current_term, hash_prev_header, hash(TxList[0]), hash(TxList[1]))
		new_header.calc_nonce()
		new_block = Block(TxList, new_header)
		self.chain.append(new_block)

if __name__ == "__main__":
	bc = Chain()
	output = bc.parse_init_file(CHAIN_INIT_FILE)
	bc.init_blockchain(output)
	bc.print_chain_json()
