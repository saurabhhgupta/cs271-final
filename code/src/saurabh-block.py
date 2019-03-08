# encoding=utf8

import hashlib
import string

CHAIN_INIT_FILE = "init_chain.txt"

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

	# ! TODO: calculate number of transactions

	# ! TODO: calculate the nonce (done)

	# ! TODO: formulate the block

	# ! TODO: display the block contents (print_blockchain)