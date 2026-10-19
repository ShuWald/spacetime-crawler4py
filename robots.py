from urllib.parse import urlparse
import re
import string

"""
Queriable representation of a robots.txt file. Example usage:
    robots = Robots("ics.uci.edu", "User-agent: *\nDisallow: /people")
    print(robots.can_crawl("MyAgent", "https://ics.uci.edu/people")) # False
"""
class Robots:
    re_useragent = re.compile(r"^\W*user-agent\W*:([^#]*)", flags=re.I)
    re_allow = re.compile(r"^\W*allow\W*:([^#]*)", flags=re.I)
    re_disallow = re.compile(r"^\W*disallow\W*:([^#]*)", flags=re.I)
    re_sitemap = re.compile(r"^\W*sitemap\W*:([^#]*)", flags=re.I)

    useragent_chars = set(string.ascii_letters + string.digits + "_")
    path_reserved = set(":/?#[]@!$&'()*+,;=") # general and special delimiters, Section 2.2 RFC3986
    path_unreserved = set(string.ascii_letters + string.digits + "-._~") # unreserved delimeters, Section 2.3 RFC3986
    path_chars = path_reserved.union(path_unreserved)

    def __init__(self, domain, user_agent, robotstxt):
        self._domain = domain
        self._user_agent = self._normalize_user_agent(user_agent)
        self._rules, self._sitemaps = self._parse_rules(robotstxt)

    @classmethod
    def _normalize_user_agent(cls, agent: str) -> str:
        return "".join(c for c in agent if c in cls.useragent_chars).lower()

    @classmethod
    def agent_matches(cls, agent, pattern) -> bool:
        if pattern == "*":
            return True
        print("comparing",cls._normalize_user_agent(pattern), agent.lower() )
        return cls._normalize_user_agent(pattern) in agent.lower()

    @classmethod
    def _pattern_regex(cls, pattern: str) -> re.Pattern:
        return re.compile("".join([".*" if c == "*" else "$" if c == "$" else re.escape(c) for c in pattern]))

    def _parse_rules(self, robotstxt: str) -> tuple[list[tuple[str, re.Pattern]], list[str]]:
        rules: list[tuple[str, re.Pattern]] = [("allow", re.compile(r""))] # By default, allow. Overriden by anything.
        sitemaps: list[str] = []
        applicable = False
        for line in robotstxt.splitlines():
            print("checking line", line, "vs", Robots.re_useragent)
            if r := Robots.re_useragent.search(line):
                print("user agent found", line)
                agent = r.group(1)
                applicable = Robots.agent_matches(self._user_agent, r.group(1).strip())
                continue
            if applicable:
                if r := Robots.re_allow.search(line):
                    rules.append(('allow', Robots._pattern_regex(r.group(1).strip())))
                elif r := Robots.re_disallow.search(line):
                    rules.append(('disallow', Robots._pattern_regex(r.group(1).strip())))
                elif r := Robots.re_sitemap.search(line):
                    sitemaps.append(r.group(1).strip())
        return rules, sitemaps

    def get_sitemaps(self):
        return [sitemap for keyword, sitemap in self._rules if keyword == 'sitemap']

    def can_crawl(self, url: str):
        """Accepts a fully-qualified URL, not a path. Asserts on url domain. TODO: Allow logging?"""
        parse = urlparse(url)
        assert parse.netloc ==  self._domain
        path = parse.path

        allow_rule_size = ("allow", "", 0)
        for allow, rule in self._rules:
            print(f"matching url {url} against rule {rule}")
            if match := rule.search(url):
                size = len(match.group())
                if size > allow_rule_size[2] or (size == allow_rule_size[2] and allow == 'allow'):
                    allow_rule_size = allow, rule, size
        return allow_rule_size[0] == 'allow'
