import unittest

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
]


URLHASH_CASES = [
    # Ignore scheme and host casing, and add the missing root path.
    {
        "inputs": [
            "HTTP://Example.COM",
            "http://example.com/",
            "https://EXAMPLE.COM",
        ],
        "output": "e52aa78cab6e854b1a7db9780b9915240467f21ce7a790328ff848ddb2869f80",
    },
    # Ignore host casing while preserving path, query, and fragment.
    {
        "inputs": [
            "https://Example.COM/path?query=1#section",
            "http://EXAMPLE.com/path?query=1#section",
        ],
        "output": "c0891be7caaaa160d45f322e841b34aaf0b16d174c8a943d0733fc43323d05e0",
    },
    # Keep distinct fragments distinct in the URL hash.
    {
        "inputs": ["https://example.com/page#one"],
        "output": "80c40f1c3ac3b1c404552d88610a8975cc291ccae4ef41b7155db12dea860595",
    },
    {
        "inputs": ["https://example.com/page#two"],
        "output": "cd6c8b2ab8c1616e98aaee99d7d8a5ce8f0544191ead5cfcf030d07cb2e23e71",
    },
]


# Recursively test the above cases
class UrlOperationsTests(unittest.TestCase):
    def test_normalize_cases(self):
        for case in NORMALIZE_CASES:
            with self.subTest(inputs=case["inputs"]):
                self.assertEqual(normalize(*case["inputs"]), case["outputs"])

    def test_get_urlhash_cases(self):
        for case in URLHASH_CASES:
            for url in case["inputs"]:
                with self.subTest(url=url):
                    self.assertEqual(get_urlhash(url), case["output"])


if __name__ == "__main__":
    unittest.main()
