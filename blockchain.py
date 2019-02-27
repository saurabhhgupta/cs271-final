# encoding=utf8

import hashlib
import string

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

class Header(object):
	'''txA and txB must be HASHED strings (SHA256).'''
	def __init__(self, currentTerm, prevBlockHeader, txA, txB):
		'''
		Current term represents the term being used in Raft.
		'''
		self.currentTerm = currentTerm

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

	'''
	Stringify
	'''
	# ! UNTESTED FUNCTION
	def stringify(self):
		return "{},{},{},{}".format(self.currentTerm, self.hashPrevBlockHeader, self.hashListOfTxs, self.nonce)		

class Block(object):
	def __init__(self, transactions, header):
		self.transactions = transactions # list of two transaction
		self.header = header

	# ! UNTESTED FUNCTION
	def calcNonce(self):
		self.header.nonce = 0
		acceptDigit = ['0','1','2']
		while hash(str(self.header.nonce) + self.header.hashListOfTxs)[-1] not in acceptDigit:
			self.header.nonce += 1


class Chain(object):
	def __init__(self):
		self.chain = []

	'''
	Assumes \n delimiter for triplets
	Returns list of transactions
	'''
	def parseInitFile(self, file):
		transactionList = []
		with open(file, 'r') as configFile:
			line = configFile.readline()
			while line:
				# line = line.strip('\n')
				source, destination, amount = line.split(' ')
				transaction = Transaction(source, destination, int(amount))
				transactionList.append(transaction)
				line = configFile.readline()
		print transactionList
		return transactionList

	'''
	Initializes the blockchain with the input transactions from the config file.
	'''
	# ! UNTESTED FUNCTION
	def initBlockChain(self, inputTransactionList):
		txPair = []
		header = None
		for index, transaction in enumerate(inputTransactionList):
			txPair.append(transaction.stringify())
			if index % 2 == 1: # if it is the 2nd transaction in the pair
				if index == 1:
					hashPrevHeader = 'NULL' 
				else:
					hashPrevHeader = hash(header.stringify())
				header = Header(0, hashPrevHeader, hash(txPair[0]), hash(txPair[1]))
				block = Block(txPair, header)
				block.calcNonce()
				self.chain.append(block)
				txPair = []

	def printChain(self):
		print self.chain

blockchain = Chain()
transactionList = blockchain.parseInitFile('test_config.txt') # ! Hardcoded file
blockchain.initBlockChain(transactionList)
	