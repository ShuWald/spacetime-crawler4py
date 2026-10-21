import unittest

from robots import Robots

class TestRobots(unittest.TestCase):
    def test_matching(self):
        # substring match
        self.assertTrue(Robots.agent_matches("MyAgent", pattern="MyAgent"))
        self.assertTrue(Robots.agent_matches("MyAgent", pattern="Agen"))
        # substring non match
        self.assertFalse(Robots.agent_matches("MyAgent", pattern="OtherAgent"))
        # star
        self.assertTrue(Robots.agent_matches("MyAgent", pattern="*"))
        # special characters
        self.assertTrue(Robots.agent_matches("Mozilla/5.0 (compatible; ExampleBot/0.1; https://www.example.com/bot.html)", pattern="ExampleBot"))

    def test_rules(self):
        a = Robots("ics.uci.edu", "MyAgent", """
            User-Agent: MyAgent
            Allow: /people
            Disallow: /home #
            Allow: /home/*help
            Disallow: /home/*help/end$
            """)
        self.assertTrue (a.can_crawl("https://ics.uci.edu/people"))
        self.assertTrue (a.can_crawl("https://ics.uci.edu/people/page"))
        self.assertFalse(a.can_crawl("https://ics.uci.edu/home"))
        self.assertFalse(a.can_crawl("https://ics.uci.edu/home/page"))
        self.assertTrue (a.can_crawl("https://ics.uci.edu/home/page/help"))
        self.assertTrue (a.can_crawl("https://ics.uci.edu/home/page/help/subhelp"))
        self.assertFalse(a.can_crawl("https://ics.uci.edu/home/page/help/end"))
        self.assertTrue (a.can_crawl("https://ics.uci.edu/home/page/help/end/pastend"))

    def test_two_agent_block(self):
        a = Robots("ics.uci.edu", "MyAgent", """
            User-Agent: MyAgent
            User-Agent: OtherAgent
            Allow: /people
            Disallow: /home
            """)
        self.assertTrue (a.can_crawl("https://ics.uci.edu/people"))
        self.assertTrue (a.can_crawl("https://ics.uci.edu/people/page"))
        self.assertFalse(a.can_crawl("https://ics.uci.edu/home"))
        self.assertFalse(a.can_crawl("https://ics.uci.edu/home/page"))

        a = Robots("ics.uci.edu", "MyAgent", """
            User-Agent: OtherAgent
            User-Agent: MyAgent
            Allow: /people
            Disallow: /home
            """)
        self.assertTrue (a.can_crawl("https://ics.uci.edu/people"))
        self.assertTrue (a.can_crawl("https://ics.uci.edu/people/page"))
        self.assertFalse(a.can_crawl("https://ics.uci.edu/home"))
        self.assertFalse(a.can_crawl("https://ics.uci.edu/home/page"))

if __name__ == "__main__":
    unittest.main()
