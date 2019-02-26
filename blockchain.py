import hashlib

'''
General hash function that returns a HASHED string
'''
def hash(data):
	return hashlib.sha256(data).hexdigest()

'''
txA and txB are two transactions where each transaction is a string in the format: ”A B amount” 
(which means A sends B an amount of 5). And there are exactly two transactions in each list of transactions(in each block).
'''

class Transaction(object):
	def __init__(self, amount, destination):
		self.amount = int(amount)
		self.source = None
		self.destination = str(destination)

	# Will most likely need a function to return the transaction itself.
	def __repr__(self):
		transaction = "money_transfer({}, {}, {})".format(self.amount, self.source, self.destination)
		return transaction

class Header(object):
	'''txA and txB must be HASHED strings (SHA256).'''
	def __init__(self, prevBlockHeader, txA, txB):
		'''
		Current term represents the term being used in Raft.
		'''
		self.currentTerm = 0

		'''
		Hheader (B − 1) is the SHA256 hash of the header of the previous block, 
		which is the SHA256 of the string concatenation of term(B - 1), Hheader(B−2), HlistOfTxs(B− 1), and the nonce.
		'''
		self.hashPrevBlockHeader = hash(prevBlockHeader)

		'''
		HlistOfTxs(B) uses the Merkel Tree data structure, 
		which is a SHA256 hash of the concatenation of two SHA256 hashes of two transactions.
		'''
		self.hashListOfTxs = hash(txA + txB)

		'''
		The nonce is a random string such that: Taking the SHA256 of the concatenation of HListOfTxs(H(X)||H(Y)) of the current block 
		and the nonce would give a resulting hash value with the last character being a digit (0-2). 
		In order to do that you will create the nonce randomly. The length of the nonce is up to you. 
		If the calculated hash value does not end with a digit between 0 and 2 (i.e. 0, 1 or 2) as its last character, 
		you will have to try another nonce again. In other words, you need to create the nonce randomly until the 
		rightmost character of the resulting hash value is a digit between (0-2).
		'''
		self.nonce = None


class Block(object):
	def __init__(self, transactions, header, proposer):
		self.transactions = transactions
		self.header = header
		self.proposer = str(proposer)

	# Function below may not work due to class iterator (quick fix: use pointer in a method outside of this class)
	# def printBlock(self):
	# 	for transaction in self.transactions:
	# 		print(str(transaction))


class Chain(object):
	def __init__(self, block):
		self.chain = []

	def parseInitFile(self, file):
		
		# TODO: 
		# 1) parse the file (file.readlines(), x = line.split(' '), x[0] = sender, x[1] = destination, x[2] = amount)
		# 2) create the chain (using attributes above)
		# 3) append to self.chain

	def printChain(self):
		print self.chain