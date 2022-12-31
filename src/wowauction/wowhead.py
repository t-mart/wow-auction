import re

from bs4 import BeautifulSoup
from yarl import URL

from wowauction.http_client import CLIENT
from wowauction.item import Item

RANK_PATTERN = re.compile(r"professions-chaticon-quality-tier(?P<rank>\d+)\.png")
QUALITY_PATTERN = re.compile(r"<!--nstart--><b class=\\\"q(?P<quality>\d+)\\\">")
VERSION_PATTERN = re.compile(
    r"Added in patch (?P<major>\d+)\.(?P<minor>\d+)\.(?P<patch>\d+)\.(?P<build>\d+)"
)


async def lookup(id_: str) -> Item:
    """
    Look up an item on wowhead by its ID.

    In the long run, this function will not be used often. It's just used to build out
    the cache initially.
    """
    url = str(URL.build(scheme="https", host="www.wowhead.com", path=f"/item={id_}"))

    response = await CLIENT.get(url, follow_redirects=True)
    source = response.text
    soup = BeautifulSoup(source, "html.parser")

    # name
    name_ele = soup.select_one("h1")
    if name_ele is None:
        raise ValueError(f"Couldn't find name of item with id {id_} ({url})")
    name = next(name_ele.stripped_strings)

    # quality
    if (quality_match := QUALITY_PATTERN.search(source)) is None:
        raise ValueError(f"Couldn't find quality of item with id {id_} ({url})")
    quality = int(quality_match.group("quality"))

    # rank
    rank: int | None = None
    if (rank_match := RANK_PATTERN.search(source)) is not None:
        rank = int(rank_match.group("rank"))  # type: ignore

    # major, minor, patch, build
    if (version_match := VERSION_PATTERN.search(source)) is None:
        raise ValueError(f"Couldn't find version of item with id {id_} ({url})")
    major = int(version_match.group("major"))
    minor = int(version_match.group("minor"))
    patch = int(version_match.group("patch"))
    build = int(version_match.group("build"))

    item = Item(
        id_=id_,
        name=name,
        quality=quality,
        rank=rank,
        major=major,
        minor=minor,
        patch=patch,
        build=build,
    )

    return item
