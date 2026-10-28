
"""Statistics is a commutative monoid. It can be kept separate across workers before joining once."""
from threading import RLock
from logging import Logger
from utils.config import Config
import urllib.parse
import re
import bs4
from collections import defaultdict
import pickle
import os
import hashlib
from collections import Counter

class Statistics:
    re_word = re.compile("[a-zA-Z_0-9']+")

    """
    Statistics uses a Config, and a restart.
    stats_file overrides the Stats save file.
    If stats_file is empty string, this Statistics
    object will not be saved.
    """
    def __init__(self, config: Config, restart: bool, logger: Logger, stats_file: str | None = None):
        self.lock = RLock()

        self._word_counts = defaultdict(lambda: 0) # all words, stopworded on query
        self._longest_page: tuple[str, int] = ("", 0) # (url, word count)
        self._urls: set[str] = set()
        self._fingerprints = set()

        self._config = config
        self._logger = logger
        self.similarity_treshold = 3

        if config.stopwords:
            with open(config.stopwords) as f:
                self._stopwords = { w.strip() for w in f.readlines() }
        # None if not saving
        self._stats_file = None if stats_file == "" else stats_file or config.stats_file

        if self._stats_file is not None:
            if restart:
                if(os.path.exists(self._stats_file)):
                    os.remove(self._stats_file)
            else:
                self.load()

    def _normalize(self, url: str) -> str:
        return urllib.parse.urldefrag(url)[0]

    """Defaults to stopwords from the config, and empty domain root."""
    def summary(self, *, stop_words: set=None, domain_root: str=""):
        with self.lock:
            dot_domain_root = "." + domain_root
            stop_words = stop_words or self._stopwords

            domain_pages: dict[str, set[str]] = defaultdict(lambda: set())
            for url in self._urls:
                domain = urllib.parse.urlparse(url).netloc
                if domain == domain_root or domain.endswith(dot_domain_root):
                    domain_pages[domain].add(self._normalize(url))
            domain_counts = sorted([(d, len(l)) for d, l in domain_pages.items()], key=lambda dl: dl[0])

            top_words = sorted([wc for wc in self._word_counts.items() if wc[0] not in stop_words], key=lambda wc: wc[1], reverse=True)
            top_words = top_words[:50]
            top_words = sorted([(word, count) for word, count in self._word_counts.items() if word not in stop_words and len(word) >= 3
                                and any(c in "aeiouy" for c in word.lower())],
                                key=lambda wc: wc[1], reverse=True
                              )
            top_words = top_words[:50]
            #print(self._urls)
            unique_pages = len(self._urls)

            return {
                "unique_page_count": unique_pages,
                "longest_page": self._longest_page,
                "top_k_words": top_words,
                "ics_subdomain_pagecounts": domain_counts
            }

    def ingest(self, url: str, parse: bs4.BeautifulSoup):
        with self.lock:
            text = parse.get_text("\n", strip=True)
            words: list[str] = self.re_word.findall(text)
            word_count = len(words)

            word_frequencies = dict(Counter(w.lower() for w in words))
            page_fingerprint = 0
            page_fingerprint = self.get_fingerprint(word_frequencies)


            has_similar = self.has_similar(page_fingerprint, self.similarity_treshold)

            if not has_similar:
                self._fingerprints.add(page_fingerprint)
                for word in words:
                    self._word_counts[word.lower()] += 1
                if word_count > self._longest_page[1]:
                    self._longest_page = (url, word_count)
                # expects normalized url input, except for fragments
                url_norm = self._normalize(url)
                self._urls.add(url_norm)

            if self._stats_file:
                self.save() # TODO: save only occasionally (same for frontier)

            return not has_similar # most instances will let this drop, but ingest will return False if a given url/page is not unique

    """Returns an anonymous statistics object with no file to save at."""
    def union(self, other: 'Statistics') -> 'Statistics':
        with self.lock:
            s = Statistics(self._config, False, self._logger, stats_file="")
            for w, c in self._word_counts.items():
                s._word_counts[w] = c
            for w, c in other._word_counts.items():
                s._word_counts[w] += c
            if self._longest_page[1] > other._longest_page[1]:
                s._longest_page = self._longest_page
            else:
                s._longest_page = other._longest_page
            s._urls = self._urls.union(other._urls)
            s._fingerprints = self._fingerprints | other._fingerprints
            return s

    # combine statistics and put into save file
    # worker will call after a set amount of pages and after crawl
    def save(self, file: str | None = None):
        with self.lock:
            if file is None and self._stats_file is None:
                if self._logger:
                    self._logger.error("Failed to load Statistics, stats file not provided")
                return

            savefile = file or self._stats_file

            store_word_counts = dict(self._word_counts)

            stats = {
                "_urls": self._urls,
                "_word_counts": store_word_counts,
                "_longest_page": self._longest_page,
                "_fingerprints": self._fingerprints,
            }

            with open(savefile, "wb") as f:
                pickle.dump(stats, f)

    # Load stats from the save file.
    def load(self, file=None):
        with self.lock:
            if file is None and self._stats_file is None:
                if self._logger:
                    self._logger.error("Failed to load Statistics, stats file not provided")
                return
            savefile = file or self._stats_file
            if not os.path.exists(savefile):
                self._logger.info("Statistics file doesn't exist yet.")
                return
            print(f"Loading stats from: {os.path.abspath(savefile)}")
            print(f"File size: {os.path.getsize(savefile)} bytes")
            with open(savefile, "rb") as f:
                stats = pickle.load(f)

            self._urls = stats["_urls"]
            self._word_counts.update(stats["_word_counts"])
            self._longest_page = stats["_longest_page"]
            self._fingerprints = stats["_fingerprints"]


    def get_hash_int(self, word: str):
        obj = hashlib.blake2b(word.encode("utf-8"), digest_size=8)
        return int(obj.hexdigest(), 16)

    def get_fingerprint(self, tokens):
        V = [0] * 64

        for token, count in tokens.items():
            hash_int = self.get_hash_int(token)

            for i in range(64):
                if(hash_int >> i) & 1:
                    V[i] += count
                else:
                    V[i] -= count

        fingerprint = 0
        for i in range(64):
            if V[i] > 0:
                fingerprint = fingerprint | (1 << i)

        return fingerprint

    def compare_fingerprints(self, f1, f2):
        return bin(f1 ^ f2).count('1')

    def has_similar(self, f2, treshold: int):
        for f1 in self._fingerprints:
            if self.compare_fingerprints(f1, f2) <= treshold:
                return True
        return False
