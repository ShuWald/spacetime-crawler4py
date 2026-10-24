from crawler.statistics import Statistics
import unittest

from scraper import scraper
from test.mock import MockRawResponse, MockResponse, MakeStats


SCRAPER_LOGIC_CASES = {
    # Reject an invalid redirect destination and return the requested URL as its alias.
    "test_invalid_redirect": {
        "inputs": (
            "https://www.ics.uci.edu/original",
            MockResponse(
                "ftp://invalid.example.com",
                200,
                raw_response=MockRawResponse(b"<html>unauthorized</html>"),
            ),
            True,
        ),
        "outputs": {
            "urls": [],
            "status": 200,
            "alias": ["https://www.ics.uci.edu/original"],
            "error": "Unauthorized redirect domain",
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
            True,
        ),
        "outputs": {
            "urls": [],
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
            True,
        ),
        "outputs": {
            "status": 200,
            "urls": [
                "https://ics.uci.edu/first",
                "https://ics.uci.edu/second",
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
            True,
        ),
        "outputs": {
            "status": 200,
            "urls": ["https://ics.uci.edu/next"],
            "destination": ["https://www.ics.uci.edu/destination"],
            "alias": ["https://www.ics.uci.edu/original"],
        },
    },
    # Reject an authorized redirect when robots.txt disallows its destination.
    "test_redirect_disallowed_by_robots": {
        "inputs": (
            "https://www.ics.uci.edu/original",
            MockResponse(
                "https://www.ics.uci.edu/disallowed",
                200,
                raw_response=MockRawResponse(
                    b'<a href="/should-not-be-scraped">link</a>'
                ),
            ),
            False,
        ),
        "outputs": {
            "urls": [],
            "status": 200,
            "alias": ["https://www.ics.uci.edu/original"],
            "error": "Redirected URL disallowed by robots.txt",
        },
    },
    # Allow a non-redirect response to be scraped regardless of redirect robots permission.
    "test_non_redirect_ignores_robots_permission": {
        "inputs": (
            "https://www.ics.uci.edu",
            MockResponse(
                "https://www.ics.uci.edu",
                200,
                raw_response=MockRawResponse(
                    b'<a href="/allowed">allowed</a>'
                ),
            ),
            False,
        ),
        "outputs": {
            "status": 200,
            "urls": ["https://ics.uci.edu/allowed"],
        },
    },
}


class ScraperLogicTests(unittest.TestCase):
    def setUp(self):
        self.statistics = MakeStats()

    def assert_scraper_case(self, case):
        actual = scraper(
            case["inputs"][0],
            case["inputs"][1],
            self.statistics,
            case["inputs"][2],
        )
        expected = case["outputs"]
        self.assertEqual(
            actual,
            expected,
            msg=f"\nActual output:\n{actual!r}\n\nExpected output:\n{expected!r}",
        )

    def assert_scraper_cases_recursively(self, case_names, index=0):
        if index == len(case_names):
            return
        self.assert_scraper_case(SCRAPER_LOGIC_CASES[case_names[index]])
        self.assert_scraper_cases_recursively(case_names, index + 1)

    def test_scraper_logic_cases(self):
        self.assert_scraper_cases_recursively(list(SCRAPER_LOGIC_CASES))


if __name__ == "__main__":
    unittest.main()
