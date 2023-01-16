from collections import defaultdict
from collections.abc import AsyncIterator, Mapping
from pathlib import Path

import anyio
import click

from wowauction.auction import Auction
from wowauction.blizzard import BlizzardAPI
from wowauction.cache import Cache
from wowauction.item import Item
from wowauction.vmagent import VMAgentAPI


async def periodic(period: float) -> AsyncIterator[None]:
    """
    Yields once every `period` seconds, taking account the time spent in the loop. The
    first iteration will yield immediately.

    If the loop takes >= `period` seconds, run the next iteration immediately.
    """
    now = await anyio.current_time()
    while True:
        yield
        await anyio.sleep_until(now + period)
        now = await anyio.current_time()


@click.command()
@click.option("--cache-path", required=True, type=click.Path(path_type=Path))
@click.option("--blizz-client-id", required=True)
@click.option("--blizz-client-secret", required=True)
@click.option("--vmagent-host", required=True)
@click.option("--vmagent-port", required=True, type=int)
@click.option(
    "--period-seconds",
    default=60 * 60,
    type=int,
    help="The number of seconds between pulls",
    show_default=True,
)
def main(
    cache_path: Path,
    blizz_client_id: str,
    blizz_client_secret: str,
    vmagent_host: str,
    vmagent_port: int,
    period_seconds: int,
) -> None:
    blizzard_api = BlizzardAPI(
        client_id=blizz_client_id, client_secret=blizz_client_secret
    )
    vmagent_api = VMAgentAPI(host=vmagent_host, port=vmagent_port)

    anyio.run(inner_loop, blizzard_api, vmagent_api, cache_path, period_seconds)


async def inner_loop(
    blizzard_api: BlizzardAPI,
    vmagent_api: VMAgentAPI,
    cache_path: Path,
    period_seconds: int,
) -> None:
    # note: this code is "async", but it doesn't really go concurrent (as of now). we
    # only really gain from being able to use this periodic function, which schedules
    # our loop. otherwise, i don't think there's much need to rearchitect for
    # concurrency: the network I/O in this project is:
    #   1. one big request to the blizzard API, or
    #   2. many little requests to localhost, which will have hardly any delay.
    # so, again, for now, i don't see the need to do any kind of async queue, etc.
    async for _ in periodic(period_seconds):
        print("starting periodic pull of auctions")

        with Cache.open(cache_path) as cache:
            total_auction_count = 0
            exported_auction_count = 0
            exported_item_ids = set()
            auctions_for_item: Mapping[Item, list[Auction]] = defaultdict(list)

            async for auction in blizzard_api.get_commodity_auctions(cache=cache):
                total_auction_count += 1

                # there's too much data coming in -- roughly 300k auctions per API call.
                # here, we do some filtering: only show common-or-better items in the
                # current expac. this reduces the number of auctions by half
                if auction.item.major < 10 or auction.item.quality < 1:
                    continue

                auctions_for_item[auction.item].append(auction)

                # await vmagent_api.export_auction(auction=auction)
                exported_auction_count += 1
                exported_item_ids.add(auction.item.id_)

            print('sorted auctions by item')

            for auctions in auctions_for_item.values():
                await vmagent_api.export_auction_summary(auctions)
                await vmagent_api.export_auction_min(auctions)

            print(
                f"exported {exported_auction_count:,} auctions for "
                f"{len(exported_item_ids):,} matching items to vmagent (of a total "
                f"{total_auction_count:,} auctions)."
            )


if __name__ == "__main__":
    main(auto_envvar_prefix="WOWAUCTION")
