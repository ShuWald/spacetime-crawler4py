import unittest

from tests.mock import MockResponse, MockRawResponse
from scraper import extract_next_links


class ExtractNextLinksTests(unittest.TestCase):
    def test_invalid_and_relative_links(self):
        # TODO: Add more invalid URL formats as the URL rules are expanded.
        response = MockResponse(
            "https://www.example.com",
            404,
            raw_response=MockRawResponse(
                b'<a href="relative-page">relative page</a>'
                b'<a href="https://www.example.com/file.pdf">invalid file</a>'
            ),
        )
        self.assertEqual(
            extract_next_links(response.url, response),
            ["https://www.example.com/relative-page"],
        )

    def test_error_response(self):
        # TODO: Check the specified handling for each response error status.
        response = MockResponse(
            "https://www.example.com",
            600,
            error="cache error",
            raw_response=MockRawResponse(b"<html><body></body></html>"),
        )
        self.assertEqual(extract_next_links(response.url, response), [])

    def test_authorized_redirect(self):
        # TODO: Check redirect status-specific behavior once redirects are modeled explicitly.
        response = MockResponse(
            "https://www.example.com/redirected",
            301,
            raw_response=MockRawResponse(
                b'<a href="/next-page">next page</a>'
                b'<a href="https://www.example.com/archive.zip">invalid file</a>'
            ),
        )

        self.assertEqual(
            extract_next_links("https://www.example.com", response),
            ["https://www.example.com/next-page"],
        )

    def test_alias_url(self):
        # TODO: Check that alias URLs are tracked without creating redirect loops.
        response = MockResponse(
            "https://www.example.com/alias",
            301,
            raw_response=MockRawResponse(
                b'<a href="/canonical-page">canonical page</a>'
            ),
        )

        self.assertEqual(
            extract_next_links("https://www.example.com/original", response),
            ["https://www.example.com/canonical-page"],
        )

    # Requires is_valid() to be complete.
    # def test_unauthorized_redirect(self):
    #     # TODO: Check that unauthorized redirects are rejected and recorded as aliases.
    #     response = MockResponse(
    #         "https://unauthorized.example.com",
    #         301,
    #         raw_response=MockRawResponse(
    #             b'<a href="/unauthorized-page">unauthorized page</a>'
    #         ),
    #     )
    #
    #     self.assertEqual(
    #         extract_next_links("https://www.example.com", response),
    #         [],
    #     )


if __name__ == "__main__":
    unittest.main()
