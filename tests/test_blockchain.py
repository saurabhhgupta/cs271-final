import unittest
from ..src import blockchain

class TestBlockchain(unittest.TestCase):
    def test_init_chain(self):
        self.assertEqual(initBlockChain(CHAIN_INIT_FILE), '[A B 5, B C 5, A C 10, C B 10, B A 15, C A 15, A B 20]')

if __name__ == "__main__":
    unittest.main()