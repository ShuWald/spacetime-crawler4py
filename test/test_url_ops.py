import unittest

from scraper import is_valid
from utils import get_urlhash, normalize


NORMALIZE_CASES = [
    # Lowercase the scheme and hostname and add a root path.
    {
        "inputs": ("HTTP://Example.COM",),
        "outputs": "http://example.com/",
    },
    # Preserve the path, query, and fragment in a normalized URL.
    {
        "inputs": ("https://Example.COM/path?query=1#section",),
        "outputs": "https://example.com/path?query=1#section",
    },
    # Remove the fragment when keepFragments is false.
    {
        "inputs": ("https://Example.COM/path?query=1#section", False),
        "outputs": "https://example.com/path?query=1",
    },
    # Add a root path when the URL has no path.
    {
        "inputs": ("https://example.com",),
        "outputs": "https://example.com/",
    },
    # Error handling for non-string URLs return empty
    {
        "inputs": (2,),
        "outputs": "",
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
    # Keep distinct fragments distinct in the URL hash.
    {
        "inputs": [
            "https://example.com/page#one",
            "https://example.com/page#two",
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
