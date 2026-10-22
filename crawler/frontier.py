import os
import shelve

from threading import Thread, RLock
from queue import Queue, Empty

from utils import get_logger, get_urlhash, normalize
from scraper import is_valid

class Frontier(object):
    def __init__(self, config, restart, verbose=False):
        self.logger = get_logger("FRONTIER")
        self.config = config
        self.to_be_downloaded = list()
        self.verbose = verbose
        
        if not os.path.exists(self.config.save_file) and not restart:
            # Save file does not exist, but request to load save.
            self.logger.info(
                f"Did not find save file {self.config.save_file}, "
                f"starting from seed.")
        elif os.path.exists(self.config.save_file) and restart:
            # Save file does exists, but request to start from seed.
            self.logger.info(
                f"Found save file {self.config.save_file}, deleting it.")
            os.remove(self.config.save_file)


        ## Imo should separate into visited and frontier/save files
    
        # Load existing save file, or create one if it does not exist.
        self.save = shelve.open(self.config.save_file)
        if restart:
            for url in self.config.seed_urls:
                self.add_url(url)
        else:
            # Set the frontier state with contents of save file.
            self._parse_save_file()
            if not self.save:
                for url in self.config.seed_urls:
                    self.add_url(url)

    def _parse_save_file(self):
        ''' This function can be overridden for alternate saving techniques. '''
        total_count = len(self.save)
        tbd_count = 0
        for url, completed in self.save.values():
            if not completed and is_valid(url):
                self.to_be_downloaded.append(url)
                tbd_count += 1
        self.logger.info(
            f"Found {tbd_count} urls to be downloaded from {total_count} "
            f"total urls discovered.")

    def get_tbd_url(self):
        try:
            next_url = self.to_be_downloaded.pop()
            if self.verbose:
                self.logger.info(f"Frontier assigning URL: {next_url}")
            return next_url
        except IndexError:
            if self.verbose:
                self.logger.info("Frontier has no URLs to assign currently.")
            # requires some kind of code to check if any workers are processing URLs in in_progress
            return None

    # URLs are saved to self.save the moment they are seen
    # This would include invalid/unauthorized URLs since our robots logic is only applied before a crawler crawls the unauthorized site
    def add_url(self, url):
        url = normalize(url)
        # Checks visited
        urlhash = get_urlhash(url)
        if urlhash not in self.save:
            self.save[urlhash] = (url, False)
            self.save.sync()
            self.to_be_downloaded.append(url)
            if self.verbose:
                self.logger.info(f"Added URL to frontier: {url}")
                self.logger.info(f"Frontier size: {len(self.to_be_downloaded)}")

    # So the instructor code indicates that urls are hashed the moment they are seen
    # Thus the saved URLs function as a "seen" set rather than a "visited" set
    def mark_url_complete(self, url):
        urlhash = get_urlhash(url)
        if urlhash not in self.save:
            # This should not happen.
            self.logger.error(
                f"Completed url {url}, but have not seen it before.")

        self.save[urlhash] = (url, True)
        self.save.sync()
