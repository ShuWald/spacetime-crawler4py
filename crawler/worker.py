from threading import Thread

from inspect import getsource
from utils.download import download
from utils import get_logger
import scraper
import time


class Worker(Thread):
    def __init__(self, worker_id, config, frontier, verbose=False):
        self.logger = get_logger(f"Worker-{worker_id}", "Worker")
        self.config = config
        self.frontier = frontier
        # basic check for requests in scraper
        assert {getsource(scraper).find(req) for req in {"from requests import", "import requests"}} == {-1}, "Do not use requests in scraper.py"
        assert {getsource(scraper).find(req) for req in {"from urllib.request import", "import urllib.request"}} == {-1}, "Do not use urllib.request in scraper.py"
        super().__init__(daemon=True)
        self.verbose = verbose
    def run(self):
        while True:
            tbd_url = self.frontier.get_tbd_url()
            if not tbd_url:
                self.logger.info("Frontier is empty. Stopping Crawler.")
                break
            resp = download(tbd_url, self.config, self.logger)
            self.logger.info(
                f"Downloaded {tbd_url}, status <{resp.status}>, "
                f"using cache {self.config.cache_server}.")

            scraped = scraper.scraper(tbd_url, resp)
            if self.verbose:
                self.logger.info(f"Scraped data: {scraped}")
            scraped_urls = scraped["urls"]
            for scraped_url in scraped_urls:
                if self.verbose:
                    self.logger.info(f"Scraped URL: {scraped_url}; attempting to append to frontier")
                self.frontier.add_url(scraped_url)
            if self.verbose:
                self.logger.info(f"Finished processing {tbd_url}")
            self.frontier.mark_url_complete(tbd_url)
            #TODO: Replace with actual politeness using smart frontier
            time.sleep(self.config.time_delay)
