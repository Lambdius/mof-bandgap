import re

from bs4 import BeautifulSoup, Tag

_UNIT_SUFFIX = re.compile(r"\s*\([^)]*\)\s*$")


def parse_properties(html: str) -> dict[str, str] | None:
    table = BeautifulSoup(html, "html.parser").find("table")
    if not isinstance(table, Tag):
        return None

    headers = [_UNIT_SUFFIX.sub("", th.get_text(strip=True)).replace(" ", "_") for th in table.find_all("th")]

    values = [td.get_text(strip=True) for td in table.find_all("td")]
    if not values:
        return None

    return dict(zip(headers, values, strict=True))
