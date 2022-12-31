from collections.abc import AsyncIterator
from pathlib import Path

import anyio
import click

from wowauction.blizzard import BlizzardAPI
from wowauction.cache import Cache
from wowauction.vmagent import VMAgentAPI


async def periodic(period: float) -> AsyncIterator[None]:
    """
    Yields once every `period` seconds, taking account the time spent in the loop.

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
    default=60 * 30,
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
        with Cache.open(cache_path) as cache:
            auction_count = 0
            async for auction in blizzard_api.get_commodity_auctions(cache=cache):
                await vmagent_api.export(auction=auction)
                auction_count += 1
            print(f"exported {auction_count} to vmagent")


if __name__ == "__main__":
    main(auto_envvar_prefix="WOWAUCTION")
