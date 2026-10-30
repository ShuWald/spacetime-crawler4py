
"""Statistics is a commutative monoid. It can be kept separate across workers before joining once."""
import time
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
        self._url_stats: dict[str, dict] = dict() # url -> {character_count, valid_character_count, word_count, counts, proportions}
        self._fingerprints = set()

        self._config = config
        self._logger = logger
        self.similarity_treshold = 3

        self.save_count = 0
        self.save_time = 0

        self._stopwords = set()
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
            unique_pages = len(self._urls)

            return {
                "unique_page_count": unique_pages,
                "longest_page": self._longest_page,
                "top_k_words": top_words,
                "ics_subdomain_pagecounts": domain_counts,
                "save_count_time": (self.save_count, self.save_time)
            }

    def ingest(self, url: str, parse: bs4.BeautifulSoup):
        # ban list of junk tokens not done
        try:
            with self.lock:
                text = parse.get_text("\n", strip=True)
                text = text.replace("\t", " ")
                text = text.replace("\r", " ")

                og_len = len(text)
                clean_text = ""
                text_error = False
                keys = ["ufffd", "invalid", "special", "stop words", "average word length"]
                counts = {k: 0 for k in keys}   # note that average word length count just stores total length of all words
                proportions = {k: 0 for k in keys}
                
                # note that average word upper bound is implemented manually (alternatives possible)
                thresholds_nums = [0.05, 0.1, 0.5, 0.1, 3.0]
                average_word_length_upper = 25.0
                thresholds = {k: v for k, v in zip(keys, thresholds_nums)}

                #\#-- ufffd, invalid, and special counts and proportions
                try:
                    counts["ufffd"] = text.count("\ufffd")
                    for ch in text:
                        # invalid if not printable ASCII (within range of 32 to 126)
                        if ch != "\n" and not (32<= ord(ch) <= 126):
                            counts["invalid"] += 1
                        else:
                            # Filter out invalids for words later?
                            clean_text += ch
                            # find special characters within printable ASCII
                            if not ch.isalnum() and not ch.isspace():
                                counts["special"] += 1

                    for key in keys[:3]:
                        proportions[key] = counts[key] / og_len if og_len > 0 else 0
                        self._logger.debug(f"URL: {url}, {key} prop: {proportions[key]}, ")
                except Exception as e:
                    self._logger.error(f"Error (ufffd, invalid, special) for {url}: {e}")
                    text_error = True
                #\#--

                #/#-- stop words and average word length counts and proportions
                words: list[str] = self.re_word.findall(clean_text if not text_error else text)
                word_count = len(words)
                try:
                    for word in words:
                        if word.lower() in self._stopwords:
                            counts["stop words"] += 1 
                        counts["average word length"] += len(word)

                    for key in keys[3:]:
                        proportions[key] = counts[key] / word_count if word_count > 0 else 0
                        self._logger.debug(f"URL: {url}, {key} prop: {proportions[key]}, ")
                except Exception as e:
                    self._logger.error(f"Error (stop words, average word length) for {url}: {e}")
                    text_error = True
                #/#--

                ##--/ log and check thresholds, if any threshold exceeded, reject page
                try:
                    for key, value in proportions.items():
                        if proportions[key] > thresholds[key]:
                            self._logger.info(f"{url} rejected due to {key} {"character " if key in keys[:3] else ""}proportion: {value} exceeded threshold {thresholds[key]}")
                            return False

                    # Manually check average word length upper threshold, alternative solutions possible
                    if (proportions["average word length"] > average_word_length_upper):
                        self._logger.info(f"{url} rejected due to average word length {proportions['average word length']} above max threshold {average_word_length_upper}")
                        return False
                except Exception as e:
                    self._logger.error(f"Error checking thresholds for {url}: {e}")
                ##--/ 

                word_frequencies = dict(Counter(w.lower() for w in words))
                page_fingerprint = 0
                page_fingerprint = self.get_fingerprint(word_frequencies)
                # This url's stats
                url_stats = {
                    "character_count": og_len,
                    "valid_character_count": len(clean_text),
                    "word_count": word_count
                }
                try:
                    url_stats["counts"] = counts
                    # Proportions can already be calculated from information above...
                    url_stats["proportions"] = proportions
                except:
                    self._logger.error(f"Can't add counts and proportions for {url}")

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
                    self._url_stats[url] = url_stats

                if self._stats_file:
                    self.save() # TODO: save only occasionally (same for frontier)

                return not has_similar # most instances will let this drop, but ingest will return False if a given url/page is not unique
        except Exception as e:
            self._logger.error(f"Unforseen error ingesting {url}: {e}")
            return True # If the recent statistics ingestion causes major errors at least read all url rather than rejecting everything

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
            s._url_stats = {**self._url_stats, **other._url_stats}
            s._fingerprints = self._fingerprints | other._fingerprints
            return s

    # combine statistics and put into save file
    # worker will call after a set amount of pages and after crawl
    def save(self, file: str | None = None):
        with self.lock:
            t1 = time.perf_counter()
            if file is None and self._stats_file is None:
                if self._logger:
                    self._logger.error("Failed to load Statistics, stats file not provided")
                return

            savefile = file or self._stats_file

            store_word_counts = dict(self._word_counts)

            stats = {
                "_urls": self._urls,
                "_url_stats": self._url_stats,
                "_word_counts": store_word_counts,
                "_longest_page": self._longest_page,
                "_fingerprints": self._fingerprints,
            }

            with open(savefile, "wb") as f:
                pickle.dump(stats, f)

            t2 = time.perf_counter()
            self.save_count += 1
            self.save_time += (t2 - t1)

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
            self._url_stats = stats["_url_stats"]
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
