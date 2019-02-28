import unittest
import os
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
        pass

    def test_header_init(self):
        pass

class TestBlock(unittest.TestCase):
    def test_block_header(self):
        pass

    def test_block_transactions(self):
        pass

    def test_mining(self):
        pass

class TestChain(unittest.TestCase):
    def setUp(self):
        pass

    def test_init_blockchain(self):
        correctTxList = ['A B 5', 'B C 5', 'A C 10', 'C B 10', 'B A 15', 'C A 15', 'A B 20']
        self.blockchain_chain = blockchain.Chain()
        output_transaction_list = self.blockchain_chain.parseInitFile(CHAIN_INIT_FILE)
        for i, transaction in enumerate(output_transaction_list):
            self.assertEqual(correctTxList[i], transaction.stringify())

    def test_blockchain(self):
        pass

if __name__ == "__main__":
    unittest.main()