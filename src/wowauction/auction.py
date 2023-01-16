from __future__ import annotations

from decimal import Decimal
from typing import Literal, Any

from attrs import frozen

from wowauction.item import Item
from wowauction.cache import Cache


@frozen
class Auction:
    item: Item
    price_gold: float
    quantity: int
    time_left: Literal["SHORT", "MEDIUM", "LONG", "VERY_LONG"]
    timestamp: float

    @classmethod
    async def from_blizz_auction(
        cls, blizz_auction_obj: Any, cache: Cache, timestamp: float
    ) -> Auction:
        id_ = blizz_auction_obj["item"]["id"]
        item = await cache.get_or_lookup(id_)

        return Auction(
            item=item,
            price_gold=blizz_auction_obj["unit_price"] / (100 * 100),
            quantity=blizz_auction_obj["quantity"],
            time_left=blizz_auction_obj["time_left"],
            timestamp=timestamp,
        )

    @property
    def time_left_minutes(self) -> int:
        """The upper bound in minutes on the time left in an auction"""
        match self.time_left:
            case "SHORT":
                return 30
            case "MEDIUM":
                return 60 * 2
            case "LONG":
                return 60 * 12
            case "VERY_LONG":
                return 60 * 48
