from crawler.statistics import Statistics
from utils import get_logger
from crawler.frontier import Frontier
from crawler.worker import Worker
import os
import time
import shelve

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
        report, report_time = "", time.time()
        report += f"----- Begin Crawl Report: {report_time} -----\n"
        report += f"We found {s['unique_page_count']} unique pages.\n"
        page, size = s["longest_page"]
        report += f"The longest page is {page} with {size} words.\n"
        report += "The top few words are:\n"
        for w, c in s["top_k_words"]:
            report += f"{w}, {c}\n"
        subdomains = s["ics_subdomain_pagecounts"]
        report += f"There are {len(subdomains)} ics.uci.edu subdomains:\n"
        for d, c in subdomains:
            report += f"{d}, {c}\n"
        save_count, save_time = s["save_count_time"]
        report += f"Spent {save_time}s saving Statistics files {save_count} times."
        report += "----- End Crawl Report -----\n"
        # Write into regular file
        with open("summary.txt", "w", encoding="utf-8") as file:
            file.write(report)

    def join(self):
        for worker in self.workers:
            worker.join()
