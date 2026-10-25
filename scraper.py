from os import stat
import re
from urllib.parse import urljoin, urlparse
import bs4
from utils import normalize

ALLOWED_DOMAINS = (
    "ics.uci.edu",
    "cs.uci.edu",
    "informatics.uci.edu",
    "stat.uci.edu",
)

# url: the URL that was used to get the page
# resp.url: the actual url of the page
# resp.status: the status code returned by the server. 200 is OK, you got the page. Other numbers mean that there was some kind of problem.
# resp.error: when status is not 200, you can check the error here, if needed.
# resp.raw_response: this is where the page actually is. More specifically, the raw_response has two parts:
#         resp.raw_response.url: the url, again
#         resp.raw_response.content: the content of the page!


# Offloaded the redirect/unauthorized URL handling to the worker, so can assume url is valid
def scraper(url, resp, statistics, robots_allowed):
    scraped_result = {}
    scraped_result["urls"] = []
    scraped_result["status"] = resp.status
    # Logic for returning error type based on status code, allowing possible retries, or alternative handling
    # Since an invalid response also results in an empty scraped result
    if resp.status != 200:
        scraped_result["error"] = resp.error
    # Mark alias if redirected 
    if url != resp.url:
        scraped_result["alias"] = [url]
        # Reject scraping if the redirected URL is not valid in some way
        # First is general validity, including checking URL within authorized domains
        if not is_valid(resp.url):
            scraped_result["error"] = "Unauthorized redirect domain"
        # Next robots.txt for specific, authorized domain
        # This has to stay after the is_valid check to avoid unnecessary robots.txt checks for invalid domains
        elif not robots_allowed:
            scraped_result["error"] = "Redirected URL disallowed by robots.txt"
        else:
            # Otherwise redirect is valid, so mark the destination URL to avoid rescraping
            # Similarity checks also avoid this
            scraped_result["destination"] = [resp.url]

    # If response content is empty
    if not resp.raw_response.content or resp.raw_response.content.strip() == "":
        scraped_result["error"] = "Dead"
    # If there are no errors can scrape URLs
    if "error" not in scraped_result:
        parser = bs4.BeautifulSoup(resp.raw_response.content, "html.parser")
        page_is_unique = statistics.ingest(resp.url, parser)
        links = extract_next_links(resp, parser)
        if page_is_unique:
            scraped_result["urls"] = links
        else:
            scraped_result["urls"] = []
    return scraped_result
        

def extract_next_links(resp, parser):
    links = []
    for a in parser.find_all("a", href = True):
        raw_href = a.get("href")
        absolute_href = urljoin(resp.url, raw_href)
        final_href = normalize(absolute_href)
        if is_valid(final_href):
            links.append(final_href)
    return links


def is_valid(url):
    if not isinstance(url, str):
        return False

    # Decide whether to crawl this url or not.
    # If you decide to crawl it, return True; otherwise return False.
    # There are already some conditions that return False.
    try:
        parsed = urlparse(url)
        if parsed.scheme not in set(["http", "https"]):
            return False
        # TODO: remove before launch
        assert parsed.hostname is not None
        hostname = parsed.hostname.lower()
        if not any(
            hostname == domain or hostname.endswith("." + domain)
            for domain in ALLOWED_DOMAINS
        ):
            return False

        return not re.match(
            r".*\.(css|js|bmp|gif|jpe?g|ico"
            + r"|png|tiff?|mid|mp2|mp3|mp4"
            + r"|wav|avi|mov|mpeg|ram|m4v|mkv|ogg|ogv|pdf"
            + r"|ps|eps|tex|ppt|pptx|doc|docx|xls|xlsx|names"
            + r"|data|dat|exe|bz2|tar|msi|bin|7z|psd|dmg|iso"
            + r"|epub|dll|cnf|tgz|sha1"
            + r"|thmx|mso|arff|rtf|jar|csv"
            + r"|rm|smil|wmv|swf|wma|zip|rar|gz)$", parsed.path.lower())

    except TypeError:
        print ("TypeError for ", parsed)
        raise
