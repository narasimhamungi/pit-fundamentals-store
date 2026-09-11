from __future__ import annotations

import time

import requests

from .config import get_settings
from .logging_config import configure_logging

log = configure_logging()


class SECClient:
    def __init__(self, session=None):
        self.s = get_settings()
        self.session = session or requests.Session()
        self.session.headers.update(
            {"User-Agent": self.s.sec_user_agent, "Accept-Encoding": "gzip, deflate"}
        )

    def get_json(self, url):
        r = self.session.get(url, timeout=self.s.sec_timeout_seconds)
        time.sleep(self.s.sec_request_delay_seconds)
        r.raise_for_status()
        return r.json()

    def companyfacts(self, cik: int):
        url = f"{self.s.sec_base_url}/api/xbrl/companyfacts/CIK{cik:010d}.json"
        log.info("operation=sec_companyfacts cik=%s", cik)
        return self.get_json(url)

    def submissions(self, cik: int):
        url = f"{self.s.sec_base_url}/submissions/CIK{cik:010d}.json"
        return self.get_json(url)


def poll_rss():
    import xml.etree.ElementTree as ET

    r = requests.get(
        "https://www.sec.gov/cgi-bin/browse-edgar?action=getcurrent&type=10-K&output=atom",
        headers={"User-Agent": get_settings().sec_user_agent},
        timeout=get_settings().sec_timeout_seconds,
    )
    r.raise_for_status()
    ns = {"a": "http://www.w3.org/2005/Atom"}
    root = ET.fromstring(r.content)
    return [
        {
            "id": e.findtext("a:id", "", namespaces=ns),
            "title": e.findtext("a:title", "", namespaces=ns),
            "updated": e.findtext("a:updated", "", namespaces=ns),
        }
        for e in root.findall("a:entry", ns)
    ]
