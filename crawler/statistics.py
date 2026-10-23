
"""Statistics is a commutative monoid. It can be kept separate across workers before joining once."""
import urllib.parse
import re
import bs4
from collections import defaultdict
class Statistics:
    re_word = re.compile("[a-zA-Z_0-9']+")

    def __init__(self):
        self._word_counts = defaultdict(lambda: 0) # all words, stopworded on query
        self._longest_page: tuple[str, int] = ("", 0) # (url, word count)
        self._urls: set[str] = set()

    def _normalize(self, url: str) -> str:
        return urllib.parse.urldefrag(url)[0]

    def summary(self, *, stop_words: set, domain_root: str):
        dot_domain_root = "." + domain_root

        domain_pages: dict[str, set[str]] = defaultdict(lambda: set())
        for url in self._urls:
            domain = urllib.parse.urlparse(url).netloc
            if domain == domain_root or domain.endswith(dot_domain_root):
                domain_pages[domain].add(self._normalize(url))
        domain_counts = sorted([(d, len(l)) for d, l in domain_pages.items()], key=lambda dl: dl[0])

        top_words = sorted([wc for wc in self._word_counts.items() if wc[0] not in stop_words], key=lambda wc: wc[1], reverse=True)
        top_words = top_words[:50]
        print(self._urls)
        unique_pages = len(self._urls)

        return {
            "unique_page_count": unique_pages,
            "longest_page": self._longest_page,
            "top_k_words": top_words,
            "ics_subdomain_pagecounts": domain_counts
        }

    def ingest(self, url: str, parse: bs4.BeautifulSoup):
        text = parse.get_text("\n", strip=True)
        words: list[str] = self.re_word.findall(text)
        word_count = len(words)
        for word in words:
            self._word_counts[word.lower()] += 1
        if word_count > self._longest_page[1]:
            self._longest_page = (url, word_count)
        # expects normalized url input, except for fragments
        url_norm = self._normalize(url)
        self._urls.add(url_norm)

    def union(self, other: Statistics) -> Statistics:
        s = Statistics()
        for w, c in self._word_counts.items():
            s._word_counts[w] = c
        for w, c in other._word_counts.items():
            s._word_counts[w] += c
        if self._longest_page[1] > other._longest_page[1]:
            s._longest_page = self._longest_page
        else:
            s._longest_page = other._longest_page
        s._urls = self._urls.union(other._urls)
        return s
