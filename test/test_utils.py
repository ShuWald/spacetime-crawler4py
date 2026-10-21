

import unittest
from utils import normalize 

class TestNormalization(unittest.TestCase):
    def testIfLowered(self):
        lowerCased = normalize("http://wWw.icS.UCI.edU/about")
        self.assertEqual(lowerCased, "http://www.ics.uci.edu/about")

    def testFragmentRemoved(self):
        removedFragment = normalize("http://www.ics.uci.edu#aaa")
        self.assertEqual(removedFragment, "http://www.ics.uci.edu")

    def testSlashRemoved(self):
        slashRemoved = normalize("http://www.ics.uci.edu/")
        self.assertEqual(slashRemoved, "http://www.ics.uci.edu")
    
    def testRemoveInsideSlash(self):
        rmSlashFragment = normalize("http://www.ics.uci.edu/bbb#aaa/")
        self.assertEqual(rmSlashFragment, "http://www.ics.uci.edu/bbb")

    def testRemoveSlashPlusFragment(self):
        rmInsideSlash = normalize("http://www.ics.uci.edu/bbb/#aaa/")
        self.assertEqual(rmInsideSlash, "http://www.ics.uci.edu/bbb")
        
if __name__ == "__main__": unittest.main()


