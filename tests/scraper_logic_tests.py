import unittest

from scraper import scraper
from tests.mock import MockRawResponse, MockResponse


class ScraperLogicTests(unittest.TestCase):
    def test_invalid_redirect(self):
        # Reject an invalid redirect destination and return the requested URL as its alias.
        response = MockResponse("ftp://invalid.example.com", 200)

        self.assertEqual(
            scraper("https://www.example.com/original", response),
            ["https://www.example.com/original"],
        )

    def test_non_success_response(self):
        # (Currently) Directly return the response status and error for retry or error handling upstream.
        response = MockResponse(
            "https://www.example.com",
            503,
            error="service unavailable",
        )

        self.assertEqual(
            scraper("https://www.example.com", response),
            [503, "service unavailable"],
        )

    def test_successful_response_returns_extracted_links(self):
        # Return normalized, valid links from a successful response.
        response = MockResponse(
            "https://www.example.com",
            200,
            raw_response=MockRawResponse(
                b'<a href="/first">first</a>'
                b'<a href="/second">second</a>'
            ),
        )

        self.assertEqual(
            scraper("https://www.example.com", response),
            [
                "https://www.example.com/first",
                "https://www.example.com/second",
            ],
        )

    def test_successful_redirect(self):
        # (Currently) Append a redirected destination so it can be tracked as an alias.
        response = MockResponse(
            "https://www.example.com/destination",
            200,
            raw_response=MockRawResponse(
                b'<a href="/next">next</a>'
            ),
        )

        self.assertEqual(
            scraper("https://www.example.com/original", response),
            [
                "https://www.example.com/next",
                "https://www.example.com/destination",
            ],
        )


if __name__ == "__main__":
    unittest.main()
