import unittest

from scraper import is_valid
from utils import get_urlhash, normalize


NORMALIZE_CASES = [
    # Basic absolute URLs are lowercased and receive a root path.
    {
        "inputs": ("HTTP://Example.COM",),
        "outputs": "http://example.com/",
    },
    # The common www. prefix is removed so equivalent deployed URLs match.
    {
        "inputs": ("https://WWW.Example.COM/path",),
        "outputs": "https://example.com/path",
    },
    # Path trailing slashes are removed, except for the root path.
    {
        "inputs": ("https://example.com/path///",),
        "outputs": "https://example.com/path",
    },
    {
        "inputs": ("https://example.com///",),
        "outputs": "https://example.com/",
    },
    # Default ports are removed, while non-default ports remain significant.
    {
        "inputs": ("HTTPS://WWW.Example.COM:443/path/",),
        "outputs": "https://example.com/path",
    },
    {
        "inputs": ("http://www.example.com:80/path/",),
        "outputs": "http://example.com/path",
    },
    {
        "inputs": ("https://www.example.com:8443/path/",),
        "outputs": "https://example.com:8443/path",
    },
    # Query strings and fragments are excluded by default.
    {
        "inputs": ("https://example.com/path?query=1#section",),
        "outputs": "https://example.com/path",
    },
    # Query and fragment retention can be enabled independently.
    {
        "inputs": ("https://example.com/path?query=1#section", True),
        "outputs": "https://example.com/path?query=1",
    },
    {
        "inputs": ("https://example.com/path?query=1#section", False, True),
        "outputs": "https://example.com/path#section",
    },
    {
        "inputs": ("https://example.com/path?query=1#section", True, True),
        "outputs": "https://example.com/path?query=1#section",
    },
    # Protocol-relative and relative inputs preserve their URL structure.
    {
        "inputs": ("//WWW.Example.COM/path/",),
        "outputs": "//example.com/path",
    },
    {
        "inputs": ("/relative/path/",),
        "outputs": "/relative/path",
    },
    {
        "inputs": ("?query=1#section",),
        "outputs": "/",
    },
]


URLHASH_CASES = [
    # Ignore scheme and host casing, and add the missing root path.
    {
        "inputs": [
            "HTTP://Example.COM",
            "http://example.com/",
            "https://EXAMPLE.COM",
        ],
        "comparison": "equal",
    },
    # Ignore host casing while preserving path, query, and fragment.
    {
        "inputs": [
            "https://Example.COM/path?query=1#section",
            "http://EXAMPLE.com/path?query=1#section",
        ],
        "comparison": "equal",
    },
    # Keep distinct paths distinct in the URL hash.
    {
        "inputs": [
            "https://example.com/page-one",
            "https://example.com/page-two",
        ],
        "comparison": "not_equal",
    },
]


class UrlOperationsTests(unittest.TestCase):
    def test_is_valid_cases(self):
        valid_urls = [
            "https://ics.uci.edu/",
            "http://www.cs.uci.edu/page",
            "https://research.informatics.uci.edu/results", # Test subdomain
            "https://stat.uci.edu/data",
        ]
        invalid_urls = [
            "https://uci.edu/",
            "https://notics.uci.edu/",
            "https://ics.uci.edu.evil.example/",
            "ftp://ics.uci.edu/file",
            "relative-page",
            None,
            2,
        ]

        for url in valid_urls:
            with self.subTest(url=url):
                self.assertTrue(is_valid(url))

        for url in invalid_urls:
            with self.subTest(url=url):
                self.assertFalse(is_valid(url))

    def test_normalize_cases(self):
        for case in NORMALIZE_CASES:
            with self.subTest(inputs=case["inputs"]):
                self.assertEqual(normalize(*case["inputs"]), case["outputs"])

    def test_get_urlhash_cases(self):
        equivalent_case = URLHASH_CASES[0]
        equivalent_hashes = [
            get_urlhash(url) for url in equivalent_case["inputs"]
        ]
        self.assertEqual(equivalent_hashes[0], equivalent_hashes[1])
        self.assertEqual(equivalent_hashes[1], equivalent_hashes[2])

        path_case = URLHASH_CASES[1]
        self.assertEqual(
            get_urlhash(path_case["inputs"][0]),
            get_urlhash(path_case["inputs"][1]),
        )

        distinct_fragment_case = URLHASH_CASES[2]
        self.assertNotEqual(
            get_urlhash(distinct_fragment_case["inputs"][0]),
            get_urlhash(distinct_fragment_case["inputs"][1]),
        )


if __name__ == "__main__":
    unittest.main()
