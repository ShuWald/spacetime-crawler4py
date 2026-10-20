
import unittest
from types import SimpleNamespace
from crawler.frontier import Frontier 
# test relative links

class NoRejectRelativeFrontier(unittest.TestCase):
    # test if non http/https gets rejected  
    def testNormalAddition(self):
        config = SimpleNamespace(save_file="test_f.shelve", seed_urls = ["http://www.ics.uci.edu"])
        frontier = Frontier(config, restart=True)
        flength = len(frontier.to_be_downloaded)
        frontier.add_url("/professors")
        self.assertEqual(len(frontier.to_be_downloaded), flength)
        frontier.save.close()

    def testCycle(self):
        config = SimpleNamespace(save_file="test_f.shelve", seed_urls = ["http://www.ics.uci.edu"])
        frontier = Frontier(config, restart=True)

        A = frontier.get_tbd_url()
        frontier.add_url("http://www.ics.edu/about")
        frontier.mark_url_complete(A)

        B = frontier.get_tbd_url()
        frontier.add_url("http://www.ics.uci.edu")

        self.assertEqual(len(frontier.to_be_downloaded), 0)
        frontier.save.close()





# test that urls get added and growth of list is by 1

# A B A 
# try additions with different spellings -> trailing slash, fragment
# check completed is true in save file after complete 
# add one url and add it again


# class (unittest.TestCase):
#     def testIfLowered(self):
#         lowerCased = normalize("http://wWw.icS.UCI.edU/about")
#         self.assertEqual(lowerCased, "http://www.ics.uci.edu/about")


        
if __name__ == "__main__": unittest.main()


