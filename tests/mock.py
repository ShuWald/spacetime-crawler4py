class MockResponse:
    def __init__(self, url, status, error=None, raw_response=None):
        self.url = url
        self.status = status
        self.error = error
        self.raw_response = raw_response

class MockRawResponse:
    def __init__(self, content=b""):
        self.content = content