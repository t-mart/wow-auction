from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from attrs import frozen

from wowauction.item import Item
from wowauction.wowhead import lookup as wowhead_lookup


@frozen
class Cache:
    con: sqlite3.Connection

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
            return Item(
                id_=id_,
                name=row["name"],
                quality=row["quality"],
                rank=row["rank"],
                major=row["major"],
                minor=row["minor"],
                patch=row["patch"],
                build=row["build"],
            )

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

    async def get_or_lookup(self, id_: str) -> Item:
        cached = self.get(id_=id_)
        if cached is not None:
            return cached
        item = await wowhead_lookup(id_=id_)
        print(f"Looked up {item.name} (id={item.id_}) because it was not in cache.")
        self.insert(item)
        return item
