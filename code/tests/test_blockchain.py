import unittest
import os
import hashlib
import json
from ..src import blockchain

CHAIN_INIT_FILE = os.path.join(os.path.dirname(os.path.realpath(__file__)), "blockchain_test_init.txt")

class TestTransaction(unittest.TestCase):
    def setUp(self):
        self.source = 'Kumar'
        self.destination = 'Harold'
        self.amount = 100
        self.blockchain_transaction = blockchain.Transaction(self.source, self.destination, self.amount)

    def test_transaction_initialization(self):
        # self.blockchain_transaction = blockchain.Transaction(source, desination, amount)
        self.assertEqual(self.blockchain_transaction.source, self.source)
        self.assertEqual(self.blockchain_transaction.destination, self.destination)
        self.assertEqual(self.blockchain_transaction.amount, self.amount)

    def test_transaction_stringify(self):
        self.assertEqual(self.blockchain_transaction.stringify(), "Kumar Harold 100")

class TestHeader(unittest.TestCase):
    def setUp(self):
        self.currentTerm = 0
        self.prevHeader = 'NULL'
        self.hashPrevHeader = hashlib.sha256('NULL'.encode('utf-8')).hexdigest()
        self.txA = 'A B 100'
        self.txB = 'B C 50'
        self.hashTxA = hashlib.sha256(self.txA.encode('utf-8')).hexdigest()
        self.hashTxB = hashlib.sha256(self.txB.encode('utf-8')).hexdigest()
        self.hashTxList = hashlib.sha256((self.hashTxA+self.hashTxB).encode('utf-8')).hexdigest()
        self.nonce = 2
        self.header = blockchain.Header(self.currentTerm, self.prevHeader, self.hashTxA, self.hashTxB)

    def test_nonce_mining(self):
        self.header.calcNonce()
        self.assertEqual(self.nonce, self.header.nonce)

    def test_header_init_and_stringify(self):
        correct_header_stringify = '{},{},{},{}'.format(0, self.hashPrevHeader, self.hashTxList, self.nonce)
        self.header.calcNonce()
        output_stringify = self.header.stringify()
        self.assertEqual(correct_header_stringify, output_stringify)

    # this was the stupidest unittest ever
    def test_createHeaderJson(self):
        correct_dict =  {'currentTerm': self.currentTerm, 
                        'hashPrevBlockHeader': self.hashPrevHeader,
                        'hashListOfTxs': self.hashTxList,
                        'nonce': self.nonce}
        self.header.calcNonce()
        self.assertEqual(json.dumps(correct_dict), self.header.createHeaderJson())

class TestBlock(unittest.TestCase):
    def setUp(self):
        self.currentTerm = 0
        self.prevHeader = 'NULL'
        self.hashPrevHeader = hashlib.sha256('NULL'.encode('utf-8')).hexdigest()
        self.txA = 'A B 100'
        self.txB = 'B C 50'
        self.transaction_list = [self.txA, self.txB]
        self.hashTxA = hashlib.sha256(self.txA.encode('utf-8')).hexdigest()
        self.hashTxB = hashlib.sha256(self.txB.encode('utf-8')).hexdigest()
        self.hashTxList = hashlib.sha256((self.hashTxA+self.hashTxB).encode('utf-8')).hexdigest()
        self.nonce = 2
        self.header = blockchain.Header(self.currentTerm, self.prevHeader, self.hashTxA, self.hashTxB)
        self.header.nonce = self.nonce
        self.block = blockchain.Block(self.transaction_list, self.header)

    # def test_block_creation(self):
    #     self.block.transactions

    # def test_createBlockJson(self):
    #     pass

class TestChain(unittest.TestCase):
    def setUp(self):
        pass

    def test_parse_init_file(self):
        correctTxList = ['A B 5', 'B C 5', 'A C 10', 'C B 10', 'B A 15', 'C A 15', 'A B 20']
        self.blockchain_chain = blockchain.Chain()
        output_transaction_list = self.blockchain_chain.parseInitFile(CHAIN_INIT_FILE)
        for i, transaction in enumerate(output_transaction_list):
            self.assertEqual(correctTxList[i], transaction.stringify())

    def test_printChainJson(self):
        self.blockchain_chain = blockchain.Chain()
        output_transaction_list = self.blockchain_chain.parseInitFile(CHAIN_INIT_FILE)
        self.blockchain_chain.initBlockChain(output_transaction_list)
        self.blockchain_chain.printChainJson()

    def test_init_blockchain(self):
        self.blockchain_chain = blockchain.Chain()
        output_transaction_list = self.blockchain_chain.parseInitFile(CHAIN_INIT_FILE)
        self.blockchain_chain.initBlockChain(output_transaction_list)
        # ! INCOMPLETE

    

if __name__ == "__main__":
    unittest.main()