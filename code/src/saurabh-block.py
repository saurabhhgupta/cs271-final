# encoding=utf8

import hashlib
from string import ascii_uppercase
from string import digits
from random import SystemRandom

CHAIN_INIT_FILE = "init_chain.txt"

# Source: https://stackoverflow.com/questions/2257441/random-string-generation-with-upper-case-letters-and-digits-in-python
def generate_string():
	return ''.join(SystemRandom().choice(ascii_uppercase + digits) for _ in range(8))

def hash(data):
	return hashlib.sha256(data.encode('utf-8')).hexdigest()

class Block(object):
	current_term = 0
	prev_header_hash = None
	current_transactions_hash = None
	nonce = None
	transaction_list = None

	def __init__(self, prev_header_hash):
		self.transaction_list = []
		self.prev_header_hash = prev_header_hash

	# ! TODO: add transaction
	def add_transaction(self, transaction):
		self.transaction_list.append(transaction)

	# ! TODO: calculate number of transactions
	def calculate_number_of_transactions(self):
		return len(self.transaction_list)

	# ! TODO: calculate the nonce (done)
	def calculate_nonce(self):
		accept_digit = ['0', '1', '2']
		self.nonce = generate_string()
		while hash(str(self.nonce) + self.current_transactions_hash)[-1] not in accept_digit:
			calculate_nonce()

	# ! TODO: formulate the block
	def formulate_block(self, term):
		tx_a, tx_b = hash(self.transaction_list[0]), hash(self.transaction_list[1])
		self.current_transactions_hash = hash(tx_a + tx_b)
		self.nonce = self.calculate_nonce()
		self.current_term = term

	# ! TODO: display the block contents (print_blockchain)
	def print_block(self, number):
		print("block # - {}".format(number))
		print("term - {}".format(self.current_term))
		print("H_header(B-1) - {}".format(self.prev_header_hash))
		print("H_txs(B) - {}".format(self.current_transactions_hash))
		print("nonce - {}".format(self.nonce))
		print("list of trans - {}".format(', '.join(self.transaction_list))