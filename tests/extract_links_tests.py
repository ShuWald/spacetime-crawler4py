import unittest

from tests.mock import MockResponse, MockRawResponse
from scraper import extract_next_links


EXTRACT_LINK_CASES = {
    # Parse multiple links, normalize valid URLs, and filter unsupported resources/invalid links.
    "test_normalize_multiple_valid_invalid_links": {
        "inputs": MockResponse(
            "https://www.example.com",
            200,
            raw_response=MockRawResponse(
                b'<a href="relative-page">relative page</a>'
                b'<a href="HTTPS://EXAMPLE.COM/other-page#section">absolute page</a>'
                b'<a href="https://www.example.com/file.pdf">invalid file(pdf)</a>'
                b'<a href="mailto:test@example.com">invalid scheme</a>'
            ),
        ),
        "outputs": [
            "https://www.example.com/relative-page",
            "https://example.com/other-page#section",
        ],
    },
    # (Currently) Return no links when the page contains no crawlable URLs.
    "test_no_valid_links": {
        "inputs": MockResponse(
            "https://www.example.com",
            200,
            raw_response=MockRawResponse(
                b'<a href="https://www.example.com/file.pdf">invalid file</a>'
            ),
        ),
        "outputs": [],
    },
}


class ExtractNextLinksTests(unittest.TestCase):
    def test_normalize_multiple_valid_invalid_links(self):
        case = EXTRACT_LINK_CASES["test_normalize_multiple_valid_invalid_links"]
        self.assertEqual(extract_next_links(case["inputs"]), case["outputs"])

    def test_no_valid_links(self):
        case = EXTRACT_LINK_CASES["test_no_valid_links"]
        self.assertEqual(extract_next_links(case["inputs"]), case["outputs"])


if __name__ == "__main__":
    unittest.main()
