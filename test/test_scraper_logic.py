from crawler.statistics import Statistics
import unittest

from scraper import scraper
from test.mock import MockRawResponse, MockResponse


SCRAPER_LOGIC_CASES = {
    # Reject an invalid redirect destination and return the requested URL as its alias.
    "test_invalid_redirect": {
        "inputs": (
            "https://www.ics.uci.edu/original",
            MockResponse("ftp://invalid.example.com", 200),
        ),
        "outputs": {
            "urls": [],
            "destination": ["ftp://invalid.example.com"],
            "alias": ["https://www.ics.uci.edu/original"],
            "error": "Unauthorized redirect",
        },
    },
    # (Currently) Directly return the response status and error for retry or error handling upstream.
    "test_non_success_response": {
        "inputs": (
            "https://www.ics.uci.edu",
            MockResponse(
                "https://www.ics.uci.edu",
                503,
                error="service unavailable",
                raw_response=MockRawResponse(
                    b'<a href="/retry">retry</a>'
                    b'<a href="/file.pdf">invalid file</a>'
                ),
            ),
        ),
        "outputs": {
            "urls": ["https://www.ics.uci.edu/retry"],
            "status": 503,
            "error": "service unavailable",
        },
    },
    # Return normalized, valid links from a successful response.
    "test_successful_response_returns_extracted_links": {
        "inputs": (
            "https://www.ics.uci.edu",
            MockResponse(
                "https://www.ics.uci.edu",
                200,
                raw_response=MockRawResponse(
                    b'<a href="/first">first</a>'
                    b'<a href="/second">second</a>'
                    b'<a href="/file.zip">invalid file</a>'
                ),
            ),
        ),
        "outputs": {
            "urls": [
                "https://www.ics.uci.edu/first",
                "https://www.ics.uci.edu/second",
            ],
        },
    },
    # (Currently) Append a redirected destination so it can be tracked as an alias.
    "test_successful_redirect": {
        "inputs": (
            "https://www.ics.uci.edu/original",
            MockResponse(
                "https://www.ics.uci.edu/destination",
                200,
                raw_response=MockRawResponse(
                    b'<a href="/next">next</a>'
                    b'<a href="/file.csv">invalid file</a>'
                ),
            ),
        ),
        "outputs": {
            "urls": ["https://www.ics.uci.edu/next"],
            "destination": ["https://www.ics.uci.edu/destination"],
            "alias": ["https://www.ics.uci.edu/original"],
        },
    },
}


class ScraperLogicTests(unittest.TestCase):
    def setUp(self):
        self.statistics = Statistics()

    def test_invalid_redirect(self):
        case = SCRAPER_LOGIC_CASES["test_invalid_redirect"]
        self.assertEqual(scraper(*case["inputs"], self.statistics), case["outputs"])

    def test_non_success_response(self):
        case = SCRAPER_LOGIC_CASES["test_non_success_response"]
        self.assertEqual(scraper(*case["inputs"], self.statistics), case["outputs"])

    def test_successful_response_returns_extracted_links(self):
        case = SCRAPER_LOGIC_CASES[
            "test_successful_response_returns_extracted_links"
        ]
        self.assertEqual(scraper(*case["inputs"], self.statistics), case["outputs"])

    def test_successful_redirect(self):
        case = SCRAPER_LOGIC_CASES["test_successful_redirect"]
        self.assertEqual(scraper(*case["inputs"], self.statistics), case["outputs"])


if __name__ == "__main__":
    unittest.main()
