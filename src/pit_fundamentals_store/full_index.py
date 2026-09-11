import csv
import io
import time

import requests

from .config import get_settings


def walk(start_year: int, end_year: int):
    s = get_settings()
    out = []
    session = requests.Session()
    session.headers["User-Agent"] = s.sec_user_agent
    for year in range(start_year, end_year + 1):
        for quarter in range(1, 5):
            url = f"https://www.sec.gov/Archives/edgar/full-index/{year}/QTR{quarter}/master.idx"
            r = session.get(url, timeout=s.sec_timeout_seconds)
            time.sleep(s.sec_request_delay_seconds)
            if r.status_code == 404:
                continue
            r.raise_for_status()
            marker = "CIK|Company Name|Form Type|Date Filed|Filename"
            if marker not in r.text:
                continue
            for row in csv.reader(
                io.StringIO(r.text.split(marker, 1)[1].lstrip("\n")), delimiter="|"
            ):
                if len(row) == 5 and row[0].isdigit():
                    out.append(
                        dict(
                            zip(
                                ("cik", "company", "form", "filed", "filename"),
                                row,
                                strict=True,
                            )
                        )
                    )
    return out
