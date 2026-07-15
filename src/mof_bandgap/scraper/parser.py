from bs4 import BeautifulSoup, Tag  # pyright: ignore[reportMissingImports]

from mof_bandgap.constants import UNIT_SUFFIX_PATTERN


def parse_properties(html: str) -> dict[str, str] | None:
    table = BeautifulSoup(html, "html.parser").find("table")
    if not isinstance(table, Tag):
        return None

    headers = [
        UNIT_SUFFIX_PATTERN.sub("", th.get_text(strip=True)).replace(" ", "_") for th in table.find_all("th")
    ]

    values = [td.get_text(strip=True) for td in table.find_all("td")]
    if not values:
        return None

    return dict(zip(headers, values, strict=True))
