import unittest

from test.mock import MockResponse, MockRawResponse
from scraper import extract_next_links


EXTRACT_LINK_CASES = {
    # Parse multiple links, normalize valid URLs, and filter unsupported resources/invalid links.
    "test_normalize_multiple_valid_invalid_links": {
        "inputs": MockResponse(
            "https://www.ics.uci.edu",
            200,
            raw_response=MockRawResponse(
                b'<a href="relative-page">relative page</a>'
                b'<a href="HTTPS://www.cs.uci.edu/other-page#section">absolute page</a>'
                b'<a href="https://www.ics.uci.edu/file.pdf">invalid file(pdf)</a>'
                b'<a href="mailto:test@example.com">invalid scheme</a>'
            ),
        ),
        "outputs": [
            "https://ics.uci.edu/relative-page",
            "https://cs.uci.edu/other-page",
        ],
    },
    # (Currently) Return no links when the page contains no crawlable URLs.
    "test_no_valid_links": {
        "inputs": MockResponse(
            "https://www.ics.uci.edu",
            200,
            raw_response=MockRawResponse(
                b'<a href="https://www.ics.uci.edu/file.pdf">invalid file</a>'
            ),
        ),
        "outputs": [],
    },
}


class ExtractNextLinksTests(unittest.TestCase):
    def assert_extract_case(self, case):
        actual = extract_next_links(case["inputs"])
        expected = case["outputs"]
        self.assertEqual(
            actual,
            expected,
            msg=f"\nActual output:\n{actual!r}\n\nExpected output:\n{expected!r}",
        )

    def test_normalize_multiple_valid_invalid_links(self):
        case = EXTRACT_LINK_CASES["test_normalize_multiple_valid_invalid_links"]
        self.assert_extract_case(case)

    def test_no_valid_links(self):
        case = EXTRACT_LINK_CASES["test_no_valid_links"]
        self.assert_extract_case(case)


if __name__ == "__main__":
    unittest.main()
