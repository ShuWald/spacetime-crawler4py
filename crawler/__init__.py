from crawler.statistics import Statistics
from utils import get_logger
from crawler.frontier import Frontier
from crawler.worker import Worker
import os

class Crawler(object):
    def __init__(self, config, restart, frontier_factory=Frontier, worker_factory=Worker):
        self.config = config
        self.logger = get_logger("CRAWLER")
        self.logger.info("Cache server connected, starting crawler.")
        self.frontier = frontier_factory(config, restart)
        self.statistics = Statistics(config, restart, self.logger) # TODO: shelve statistics? parallelize them?

        self.workers = list()
        self.worker_factory = worker_factory

    def start_async(self):
        self.workers = [
            self.worker_factory(worker_id, self.config, self.frontier, self.statistics)
            for worker_id in range(self.config.threads_count)]
        for worker in self.workers:
            worker.start()

    def start(self):
        try:
            self.start_async()
            self.join()
        except Exception as e:
            print(f"Crawler failed with exception {e}")
        finally:
            try:
                self.statistics.save()
            except Exception as d:
                print(f"Crawler failed to save statistics during previous error: {d}")
            # self.frontier.save()
            self.printSummary()

    def printSummary(self):
        s = self.statistics.summary(domain_root="ics.uci.edu")
        print("----- Begin Crawl Report -----")
        print(f"We found {s['unique_page_count']} unique pages.")
        page, size = s["longest_page"]
        print(f"The longest page is {page} with {size} words.")
        print("The top few words are:")
        for w, c in s["top_k_words"]:
            print(f"{w}, {c}")
        subdomains = s["ics_subdomain_pagecounts"]
        print(f"There are {len(subdomains)} ics.uci.edu subdomains:")
        for d, c in subdomains:
            print(f"{d}, {c}")
        save_count, save_time = s["save_count_time"]
        print(f"Spent {save_time}s saving Statistics files {save_count} times.")
        print("----- End Crawl Report -----")

    def join(self):
        for worker in self.workers:
            worker.join()
