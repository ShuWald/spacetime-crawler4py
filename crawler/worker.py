from threading import Thread
from inspect import getsource
from utils.download import download
from utils import get_logger
from urllib.parse import urlparse
from urllib.parse import urlunparse
import scraper
import time
import datetime
from robots import Robots

class Worker(Thread):

    robots_cache = {} # stores a dictionary of domains -> robot object for quick access to robot objects
    # Robot(domain, user_agent, loaded robot file)
    timestamp_cache = {} # stores a dictionary of domains -> timestamp for last domain access

    def __init__(self, worker_id, config, frontier):
        self.logger = get_logger(f"Worker-{worker_id}", "Worker")
        self.config = config
        self.frontier = frontier
        # basic check for requests in scraper
        assert {getsource(scraper).find(req) for req in {"from requests import", "import requests"}} == {-1}, "Do not use requests in scraper.py"
        assert {getsource(scraper).find(req) for req in {"from urllib.request import", "import urllib.request"}} == {-1}, "Do not use urllib.request in scraper.py"
        super().__init__(daemon=True)
        
    def run(self):
        while True:
            tbd_url = self.frontier.get_tbd_url() # string!

            if not tbd_url:
                self.logger.info("Frontier is empty. Stopping Crawler.")
                break

            parse_url = urlparse(tbd_url)
            domain = parse_url.netloc
            if self.robots_cache.get(domain) == None: # never before seen domain, add Robot to cache
                self._update_cache(tbd_url, parse_url)

            if self.robots_cache[domain].can_crawl(tbd_url): # check if we can crawl
                # if domain timestamp is not far enough in past:
                # wait
                resp = download(tbd_url, self.config.USERAGENT, self.logger)
                # have frontier update its list of visited URLs
                # add recent timestamp to timestamp_cache in frontier
                self.logger.info(
                    f"Downloaded {tbd_url}, status <{resp.status}>, "
                    f"using cache {self.config.cache_server}.")
                scraped_urls = scraper.scraper(tbd_url, resp)
                for scraped_url in scraped_urls:
                    self.frontier.add_url(scraped_url)
                self.frontier.mark_url_complete(tbd_url)
                time.sleep(self.config.time_delay) # remove soon

                


    def _update_cache(self, tbd_url, parse_url):
        '''updates robots_cache'''
        robots_url = urlunparse((parse_url.scheme, parse_url.netloc, "", "", "", ""))

        robots_txt = download(robots_url, self.config, self.logger)

        Worker.robots_cache[parse_url.netloc] = Robots(parse_url.netloc, self.config, robots_txt)

        time.sleep(self.config.time_delay) # delete if no need for downtime after acessing a robots.txt

    def _timestamp(self, domain):
        '''given a domain, add it into the timestamp_cache with the current timestamp'''
        pass
    
