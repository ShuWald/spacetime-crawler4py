from crawler.statistics import Statistics
class MockResponse:
    def __init__(self, url, status, error=None, raw_response=None):
        self.url = url
        self.status = status
        self.error = error
        self.raw_response = raw_response

class MockRawResponse:
    def __init__(self, content=b""):
        self.content = content


class MockConfig:
    def __init__(self):
        self.stopwords = "stopwords.txt"
        self.stats_file = "bad"

def MakeStats():
    return Statistics(MockConfig(), False, None, "")
