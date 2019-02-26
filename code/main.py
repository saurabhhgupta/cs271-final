import threading

JSON_FILE = "config.json"

mutex_lock = threading.Lock()
raft_lock = threading.Lock()

class Transaction(object):
	def __init__(self, amount, destination):
		self.amount = int(amount)
		self.source = None
		self.destination = str(destination)

	# Will most likely need a function to return the transaction itself.
	def __repr__(self):
		transaction = "money_transfer({}, {}, {})".format(self.amount, self.source, self.destination)
		return transaction

class Block(object):
	def __init__(self, transactions, proposer):
		self.transactions = transactions
		self.proposer = str(proposer)
		self.header

	# Function below may not work due to class iterator (quick fix: use pointer in a method outside of this class)
	# def print_block(self):
	# 	for transaction in self.transactions:
	# 		print(str(transaction))

# TODO: complete blockchain object
class BlockChain(object):
	def __init__(self, block):
		self.blockchain = []

	# TODO: print current blockchain
	def print_blockchain():
		pass

def parse_config(json_file):
	with open(str(json_file), "r") as file:
		# TODO: parse and assign to global values
		return