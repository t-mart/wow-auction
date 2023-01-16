from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from attrs import field, frozen

from wowauction.item import Item
from wowauction.wowhead import lookup as wowhead_lookup


@frozen
class Cache:
    con: sqlite3.Connection

    # i see that you like caches, we put a cache in your cache so you can cache while
    # you cache.
    # so, the hierarchy is: in-memory cache, sqlite, wowhead
    in_memory: dict[str, Item] = field(factory=dict)

    @classmethod
    def _create_tables(cls, con: sqlite3.Connection) -> None:
        with con:
            con.execute(
                """
                CREATE TABLE IF NOT EXISTS item
                (
                    id INTEGER PRIMARY KEY,
                    name STRING,
                    quality INTEGER,
                    rank INTEGER,
                    major INTEGER,
                    minor INTEGER,
                    patch INTEGER,
                    build INTEGER
                );
            """
            )

    @classmethod
    @contextmanager
    def open(cls, path: Path) -> Iterator[Cache]:
        path.parent.mkdir(parents=True, exist_ok=True)
        con = sqlite3.Connection(path)
        con.row_factory = sqlite3.Row
        cls._create_tables(con)
        yield cls(con=con)
        con.close()

    def get(self, id_: str) -> Item | None:
        if id_ in self.in_memory:
            return self.in_memory[id_]

        with self.con:
            result = self.con.execute(
                """
                SELECT *
                FROM item WHERE item.id = :id;
                """,
                {"id": id_},
            )
            if (row := result.fetchone()) is None:
                return None
            item = Item(
                id_=id_,
                name=row["name"],
                quality=row["quality"],
                rank=row["rank"],
                major=row["major"],
                minor=row["minor"],
                patch=row["patch"],
                build=row["build"],
            )
            self.in_memory[id_] = item
            return item

    def insert(self, item: Item) -> None:
        with self.con:
            self.con.execute(
                """
                INSERT INTO item (id, name, quality, rank, major, minor, patch, build)
                VALUES (:id, :name, :quality, :rank, :major, :minor, :patch, :build)
                """,
                {
                    "id": item.id_,
                    "name": item.name,
                    "quality": item.quality,
                    "rank": item.rank,
                    "major": item.major,
                    "minor": item.minor,
                    "patch": item.patch,
                    "build": item.build,
                },
            )
        self.in_memory[item.id_] = item

    async def get_or_lookup(self, id_: str) -> Item:
        cached = self.get(id_=id_)
        if cached is not None:
            return cached
        item = await wowhead_lookup(id_=id_)
        print(f"Looked up {item.name} (id={item.id_}) because it was not in cache.")
        self.insert(item)
        return item
