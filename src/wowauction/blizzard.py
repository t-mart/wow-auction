from collections.abc import AsyncIterable

import arrow
from attrs import frozen

from wowauction.auction import Auction
from wowauction.cache import Cache
from wowauction.http_client import CLIENT


@frozen
class BlizzardAPI:
    client_id: str
    client_secret: str

    async def get_commodity_auctions(self, cache: Cache) -> AsyncIterable[Auction]:
        token_response = await CLIENT.post(
            "https://oauth.battle.net/token",
            data={"grant_type": "client_credentials"},
            auth=(self.client_id, self.client_secret),
        )
        response_json = token_response.json()

        access_token = response_json["access_token"]

        commodities_response = await CLIENT.get(
            "https://us.api.blizzard.com/data/wow/auctions/commodities",
            params={
                "namespace": "dynamic-us",
                "locale": "en_US",
                "access_token": access_token,
            },
        )

        access_time = arrow.get().timestamp()

        for blizz_auction_obj in commodities_response.json()["auctions"]:
            yield await Auction.from_blizz_auction(
                blizz_auction_obj=blizz_auction_obj, cache=cache, timestamp=access_time
            )
