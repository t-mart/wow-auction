# wow-auction

A set of Grafana dashboards for World of Warcraft _commodities_. Goal is to look like stock charts.

As far as I can tell, _commodities_ are things that are commonly sold and that have cross-realm
auction house access. These things have good trade volume, and you can make some good money on them
🤞.

## Running

1. Copy `template.env` to `.env` and fill in the values for the variables there. You'll need a
   Blizzard Client API ID and secret, which you can create
   [here](https://develop.battle.net/access/clients).
2. Run `make up` to start the docker compose. Once the item cache is filled in (this repo ships with
   a prepopulated one by default), then navigate to <https://localhost:3000>.

   `make down` and `make restart` shut down and restart the containers.

## How it works

1. Pull all the auctions on Blizzard's WoW commodity endpoint at
   [/data/wow/auctions/commodities](https://develop.battle.net/documentation/world-of-warcraft/game-data-apis).
2. Because these auctions have only item IDs, fill in the name, quality, tier, etc from our sqlite
   cache, stored at `cache/item.db`. To fill the cache for the first time, we scrape Wowhead. Note
   the cache is persisted to disk, so we only will have to scrape once per item.
3. Insert the populated auctions into VictoriaMetrics, our metrics backend.
4. Visualize those metrics with grafana.
5. Repeat on some frequency of seconds.

## Item "Rank"?

You know... the new system in Dragonflight where items can be of varying quality/rank/tier.

Even Blizzard can't figure out what they want to call this. In tooltips, they call it "quality",
but that term already has a definition: poor/common/uncommon/rare/epic/etc.

Many players call it _rank_, so we'll use that.

For example: Serevite Ore

- Rank 1: https://www.wowhead.com/item=190395/serevite-ore
- Rank 2: https://www.wowhead.com/item=190396/serevite-ore
- Rank 3: https://www.wowhead.com/item=190394/serevite-ore

Note: These are 1-indexed (while quality is 0-indexed).

## Notes

commodities endpoint gives us auctions with:

- item id
- gold price
- quantity
- time left

but, to be useful, i also want:

- item name (source: blizz API or wowhead)
  - item quality (source: wowhead)
  - item rank (source: wowhead)
- version added (source: wowhead, blizz API, ItemVersion DB)

metrics (gauge type) should then look like

- timestamp: 1583865146520 (unix time)
- value: 5.6523 (means 5 gold, 65 silver, 23 copper)
- labels:
  - id: 12345
  - name: "The Unknown Item"
  - major: 10
  - minor: 1
  - patch: 5
  - build: 345767
