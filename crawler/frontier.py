import os
import shelve

from threading import Thread, RLock
from queue import Queue, Empty

from utils import get_logger, get_urlhash, normalize
from scraper import is_valid

from urllib.parse import urlparse
import time

class Frontier(object):
    def __init__(self, config, restart):
        self.logger = get_logger("FRONTIER")
        self.config = config
        self.to_be_downloaded = {} # stores domain : list[url]
        self.in_use = {}           # stores domain : list[url]
        self.timestamps = {}        # stores domain : date
        
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
        print("_parse save file")

        total_count = len(self.save)
        tbd_count = 0
        for url, completed in self.save.values():
            if not completed and is_valid(url):
                domain = urlparse(url).netloc;

                if domain in self.to_be_downloaded: # saved one before
                    self.to_be_downloaded[domain].append(url)
                else: # fresh domain
                    self.to_be_downloaded[domain] = [url]

                self.timestamps[domain] = None

                tbd_count += 1

        self.logger.info(
            f"Found {tbd_count} urls to be downloaded from {total_count} "
            f"total urls discovered.")

    def get_tbd_url(self):
        print("tbd_url")

        try:
            # check datetime, return first instance with long enough or first instance of a None stored time
            mintime = None
            minkey = None
            now = time.time()
            for key in list(self.timestamps):
                key_in_use = key in self.in_use

                if (key == None or (now - self.timestamps[key] >= 0.5)) and not key_in_use: # i.e valid key found
                    # do things
                    self.in_use[key] = self.to_be_downloaded[key] # store the key and list of urls
                    self.to_be_downloaded.pop(key, None)          # remove key value pair from dicctionary so we literally cant come across it, and slightly faster traversal
                    return (self.in_use[key].pop(), self.timestamps[key], False)            # return frontmost url in domain url list
                    

                elif not key_in_use: # key domain not in use but timed out
                    if (mintime == None) or self.timestamps[key] < mintime: # found older access or no time stored
                        mintime = self.timestamps[key]
                        minkey = key
                else: # domain in use
                    pass
            
            # if we get to this point, then we havent found valid domain within time (aka for all times in timestamps, now - timestamp <= 0.5), so wait and try again
            self.in_use[minkey] = self.to_be_downloaded[minkey]
            self.to_be_downloaded.pop(minkey, None)
            # if key at minkey cant be accessed, i.e to_be_downloaded is empty, will throw value error, in which case we return None
            return (self.in_use[minkey].pop(), self.timestamps[minkey], True)
        
        except IndexError:
            return (None, None, None)
        except Exception:
            return (None, None, None)

    def add_url(self, url):
        url = normalize(url)
        urlhash = get_urlhash(url)
        if urlhash not in self.save:
            self.save[urlhash] = (url, False)
            self.save.sync()

            domain = urlparse(url).netloc

            if domain in self.to_be_downloaded: # domain exists in to_be_downloaded
                self.to_be_downloaded[domain].append(url)
            elif domain in self.in_use:      # domain exists in in_use
                self.in_use[domain].append(url)
            else:                               # domain never accessed
                self.to_be_downloaded[domain] = [url]
                self.timestamps[domain] = None          # save timestamp as never accessed domain since weve never seen it

            
    
    def mark_url_complete(self, url):
        urlhash = get_urlhash(url)

        domain = urlparse(url).netloc

        self.to_be_downloaded[domain] = self.in_use[domain] # add back into to_be_downloaded domain
        self.in_use.pop(domain, None)                          # remove from in_use
        self.timestamps[domain] = time.time()

        if urlhash not in self.save:
            # This should not happen.
            self.logger.error(
                f"Completed url {url}, but have not seen it before.")

        self.save[urlhash] = (url, True)
        self.save.sync()
