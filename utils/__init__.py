import os
import logging
from hashlib import sha256
from urllib.parse import urlparse, urlsplit, urlunsplit

def get_logger(name, filename=None):
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    if not os.path.exists("Logs"):
        os.makedirs("Logs")
    fh = logging.FileHandler(f"Logs/{filename if filename else name}.log")
    fh.setLevel(logging.DEBUG)
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    formatter = logging.Formatter(
       "%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    fh.setFormatter(formatter)
    ch.setFormatter(formatter)
    # add the handlers to the logger
    logger.addHandler(fh)
    logger.addHandler(ch)
    return logger


def get_urlhash(url):
    normalized_url = normalize(url) # Currently normalizes while keeping fragments
    parts = urlsplit(normalized_url)

    # Still everything except the scheme
    hash_input = urlunsplit((
        "",              # Exclude scheme
        parts.netloc,
        parts.path,
        parts.query,
        parts.fragment
    ))

    return sha256(hash_input.encode("utf-8")).hexdigest()

# Normalize a URL, lowercases the scheme and netloc, ensures a path, and optionally keeps fragments
def normalize(url, keepFragments=True):
    parts = urlsplit(url)
    scheme = parts.scheme.lower()
    netloc = parts.netloc.lower()
    path = parts.path or "/"
    fragment = parts.fragment if keepFragments else ""

    return urlunsplit((
        scheme,
        netloc,
        path,
        parts.query,
        fragment
    ))
