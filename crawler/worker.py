from crawler.statistics import Statistics
from threading import Thread
from inspect import getsource
from utils.download import download
from utils import get_logger
from urllib.parse import urlparse
from urllib.parse import urlunparse
import time
import datetime
from scraper import scraper, is_valid
from robots import Robots

class Worker(Thread):

    robots_cache = {} # stores a dictionary of domains -> robot object for quick access to robot objects
    # Robot(domain, user_agent, loaded robot file)
    timestamp_cache = {} # stores a dictionary of domains -> timestamp for last domain access

    def __init__(self, worker_id, config, frontier, statistics):
        self.logger = get_logger(f"Worker-{worker_id}", "Worker")
        self.config = config
        self.frontier = frontier
        self.statistics = statistics
        # basic check for requests in scraper
        assert {getsource(scraper).find(req) for req in {"from requests import", "import requests"}} == {-1}, "Do not use requests in scraper.py"
        assert {getsource(scraper).find(req) for req in {"from urllib.request import", "import urllib.request"}} == {-1}, "Do not use urllib.request in scraper.py"
        super().__init__(daemon=True)

    def run(self):
        while True:
            tbd_url, timestamp, downtime_needed = self.frontier.get_tbd_url() # string, float
            if timestamp is not None:
                time_diff = time.time() - timestamp

                if time_diff >= self.config.time_delay:
                    downtime = 0.0
                
                else:
                    downtime = self.config.time_delay - time_diff
                    time.sleep(downtime)

            if not tbd_url:
                # Frontier is empty, check if any workers are currently crawling
                if not self.frontier.in_use:
                    self.logger.info("Frontier is empty and no workers currently crawling. Terminating worker.")
                    break
                else: 
                    # Wait half the politeness delay to recheck frontier
                    time.sleep(self.config.time_delay/2)
                    continue

            try: # in the event that the URL causes an error so catastrophic none of the other modules can handle it, skip the url
                parse_url = urlparse(tbd_url)
                domain = parse_url.netloc

                if self.robots_cache.get(domain) == None: # never before seen domain, add Robot to cache
                    self._update_cache(tbd_url, parse_url)

                if self.robots_cache[domain].can_crawl(tbd_url): # check if we can crawl
                    # if domain timestamp is not far enough in past:
                    # wait
                    resp = download(tbd_url, self.config, self.logger)
                    # have frontier update its list of visited URLs
                    # add recent timestamp to timestamp_cache in frontier
                    self.logger.info(
                        f"Downloaded {tbd_url}, status <{resp.status}>, "
                        f"using cache {self.config.cache_server}.")

                    # This is duplicate logic for checking redirects outside robots.txt
                    # Its ugly but I'd rather not break up the scraped_result object and pass it down
                    # And the recommendation was to keep all error/validation logic in scraper to allow unit testing
                    if is_valid(resp.url):
                        redirect_robots_allowed = True
                        destination = urlparse(resp.url)
                        if self.robots_cache.get(destination.netloc) == None: 
                            self._update_cache(resp.url, destination)
                        if not self.robots_cache[destination.netloc].can_crawl(resp.url):
                            redirect_robots_allowed = False
                    # Doesn't work, removing from frontier early affects scraping
                    # ~~Minor optimization; marking the URL as complete early to update robots cache (avoiding recrawling robots.txt)~~
                    #self.frontier.mark_url_complete(tbd_url)

                    scraped_result = scraper(tbd_url, resp, self.statistics, redirect_robots_allowed)
                    self.logger.info(f"Scraped result for URL {tbd_url}: {scraped_result}")
                    links = scraped_result.get("urls", [])
                    for link in links:
                        self.frontier.add_url(link)
                    self.frontier.mark_url_complete(tbd_url)
                
                # TODO: mark incomplete otherwise
                # key "urls" being missing currently indicates failure to load

                    # TODO: replace with proper politeness delays via frontier
                    #time.sleep(self.config.time_delay) 
            except Exception as e:
                self.logger.error(f"Exception occurred while scraping URL: {e}")
                # TODO: add bad URLs to lists in frontier once implemented




    def _update_cache(self, tbd_url, parse_url):
        '''updates robots_cache'''
        robots_url = urlunparse((parse_url.scheme, parse_url.netloc, "robots.txt", "", "", ""))

        robots_response = download(robots_url, self.config, self.logger)

        robots_txt = robots_response.raw_response.text if robots_response.raw_response is not None else "" # access the text of the robots file loaded via the pickle in response

        Worker.robots_cache[parse_url.netloc] = Robots(parse_url.netloc, self.config.user_agent, robots_txt)


        self.logger.info(f"Cached Robots.txt for {parse_url.netloc}")

        time.sleep(self.config.time_delay) # delete if no need for downtime after acessing a robots.txt

    def _timestamp(self, domain):
        '''given a domain, add it into the timestamp_cache with the current timestamp'''
        pass
