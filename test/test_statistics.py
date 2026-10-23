import unittest.async_case
import bs4
from crawler.statistics import Statistics

class StatisticsTests(unittest.TestCase):
    sample_a = bs4.BeautifulSoup("""
    b'<a href="relative-page">relative page</a>'
    b'<a href="HTTPS://www.cs.uci.edu/other-page#section">absolute page</a>'
    b'<a href="https://www.ics.uci.edu/file.pdf">invalid file(pdf)</a>'
    b'<a href="mailto:test@example.com">invalid scheme</a>'""", "html.parser")

    sample_b = bs4.BeautifulSoup("""
    <html><head><title>The Dormouse's story</title></head>
    <body>
    <p class="title"><b>The Dormouse's story</b></p>

    <p class="story">Once upon a time there were three little sisters; and their names were
    <a href="http://example.com/elsie" class="sister" id="link1">Elsie</a>,
    <a href="http://example.com/lacie" class="sister" id="link2">Lacie</a> and
    <a href="http://example.com/tillie" class="sister" id="link3">Tillie</a>;
    and they lived at the bottom of a well.</p>

    <p>Use "page" a couple more times ... make page popular.</p>

    <p class="story">...</p>""", "html.parser")

    sample_c = bs4.BeautifulSoup("""
    <p>Known set of these words words words set.</p>
    """, "html.parser")

    sample_d = bs4.BeautifulSoup("""
    <p>words</p>
    """, "html.parser")

    def test_stats(self):
        a = Statistics()

        a.ingest("https://fakeA.ics.uci.edu/page", self.sample_c)
        summary = a.summary(stop_words={"of", "these"}, domain_root="ics.uci.edu")
        self.assertEqual(summary["unique_page_count"], 1)
        self.assertEqual(summary["longest_page"], ("https://fakeA.ics.uci.edu/page", 8))
        self.assertEqual(summary["top_k_words"], [("words", 3), ("set", 2), ("known", 1)]) # order does not matter
        self.assertEqual(summary["ics_subdomain_pagecounts"], [("fakeA.ics.uci.edu", 1)])

        a.ingest("https://fakeA.ics.uci.edu/page#top", self.sample_c)
        a.ingest("https://fakeC.ics.uci.edu/page", self.sample_c)
        a.ingest("https://fakeC.ics.uci.edu/short", self.sample_d)
        a.ingest("https://fakeB.ics.uci.edu/page", self.sample_c)
        a.ingest("https://fakeB.ics.uci.edu/repeated", self.sample_c)
        summary = a.summary(stop_words={"of", "these"}, domain_root="ics.uci.edu")
        self.assertEqual(summary["unique_page_count"], 5)
        self.assertEqual(summary["longest_page"], ("https://fakeA.ics.uci.edu/page", 8))
        self.assertEqual(summary["top_k_words"], [("words", 5*3+1), ("set", 5*2), ("known", 5*1)]) # order does not matter
        self.assertEqual(summary["ics_subdomain_pagecounts"], [("fakeA.ics.uci.edu", 1), ("fakeB.ics.uci.edu", 2), ("fakeC.ics.uci.edu", 2)])

    def test_union(self):
        a = Statistics()
        a.ingest("https://ics.uci.edu/something", self.sample_a)
        b = Statistics()
        b.ingest("https://example.com/story", self.sample_b)

        ab1 = Statistics()
        ab1.ingest("https://ics.uci.edu/something", self.sample_a)
        ab1.ingest("https://example.com/story", self.sample_b)

        ab2 = a.union(b)

        summary1 = ab1.summary(stop_words={"the", "a"}, domain_root="ics.uci.edu")
        summary2 = ab2.summary(stop_words={"the", "a"}, domain_root="ics.uci.edu")
        self.assertEqual(summary1, summary2)
