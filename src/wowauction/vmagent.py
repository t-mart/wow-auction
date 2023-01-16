from __future__ import annotations

import csv
import io
from collections.abc import Iterable
from typing import Any, Literal

from attrs import frozen
from yarl import URL

from wowauction.auction import Auction
from wowauction.http_client import CLIENT
from wowauction.item import Item


@frozen
class _CSVRule:
    type_: Literal["label", "metric", "time"]
    name: str
    value: Any


@frozen
class _CSVRuleCollection:
    """
    The URL and data for importing arbitrary data into VictoriaMetrics,
    https://docs.victoriametrics.com/Single-server-VictoriaMetrics.html#how-to-import-csv-data
    """

    url_format_parameter_value: str
    post_data: str

    @classmethod
    def from_rules(cls, rules: Iterable[_CSVRule]) -> _CSVRuleCollection:
        csv_records = []
        param_records = []

        for idx, rule in enumerate(rules, start=1):
            csv_records.append(rule.value)
            param_records.append(f"{idx}:{rule.type_}:{rule.name}")

        csv_output = io.StringIO()
        csv_writer = csv.writer(csv_output)
        csv_writer.writerow(csv_records)
        post_data = csv_output.getvalue()
        csv_output.close()

        url_format_parameter_value = ",".join(param_records)

        return _CSVRuleCollection(
            url_format_parameter_value=url_format_parameter_value, post_data=post_data
        )

    def url(self, host: str, port: int) -> str:
        return str(
            URL.build(
                scheme="http",
                host=host,
                port=port,
                path="/api/v1/import/csv",
                query={"format": self.url_format_parameter_value},
            )
        )


@frozen
class VMAgentAPI:
    host: str
    port: int

    @staticmethod
    def _label_rules_for_item(item: Item) -> Iterable[_CSVRule]:
        return [
            _CSVRule("label", "id", item.id_),
            _CSVRule("label", "name", item.name),
            _CSVRule("label", "quality", item.quality),
            _CSVRule("label", "rank", item.rank),
            _CSVRule("label", "major", item.major),
            _CSVRule("label", "minor", item.minor),
            _CSVRule("label", "patch", item.patch),
            _CSVRule("label", "build", item.build),
        ]

    async def export_auction(self, auction: Auction) -> None:
        rule_collection = _CSVRuleCollection.from_rules(
            [
                *self._label_rules_for_item(auction.item),
                _CSVRule("metric", "auction_price_gold", auction.price_gold),
                _CSVRule("metric", "auction_items_total", auction.quantity),
                _CSVRule(
                    "metric", "auction_time_left_minutes", auction.time_left_minutes
                ),
                _CSVRule("time", "unix_s", int(auction.timestamp)),
            ]
        )

        await CLIENT.post(
            url=rule_collection.url(self.host, self.port),
            content=rule_collection.post_data,
        )

    async def export_auction_summary(self, auctions: list[Auction]) -> None:
        """
        Export a "summary" of auctions (which must be of the same item). This summary
        includes pricing quantiles, a total count of items, and a total sum of the
        auction prices.

        The method for calculating the quantiles is to use the nearest observation that
        is greater actual percentile (or whatever... dunno how to describe. see code)

        See https://prometheus.io/docs/concepts/metric_types/#summary for metric detail.
        """
        # we sort it literally, but just in case edits down the road
        phis = sorted([0.5, 0.75, 0.9, 0.95, 0.99, 0.999, 1])
        percentiles = {}

        total_items = sum(auction.quantity for auction in auctions)
        items_seen = 0
        phi_index = 0
        auctions_sorted_by_price = sorted(
            auctions, key=lambda a: a.price_gold, reverse=True
        )
        for auction in auctions_sorted_by_price:
            items_seen += auction.quantity

            cur_percent = items_seen / total_items

            while phis[phi_index] < cur_percent and phi_index < len(phis):
                percentiles[phis[phi_index]] = auction.price_gold
                phi_index += 1

            # in case we don't include 1, we can fast break
            if phi_index == len(phis):
                break

        # # for when we do include 1, we need to check after all auctions
        if phi_index < len(phis):
            percentiles[phis[phi_index]] = auctions_sorted_by_price[-1].price_gold

        item_rules = self._label_rules_for_item(auctions[0].item)

        # send quantiles
        for phi, percentile in percentiles.items():
            quantile_rule_collection = _CSVRuleCollection.from_rules(
                [
                    *item_rules,
                    _CSVRule("label", "quantile", phi),
                    _CSVRule("metric", "auction_price_gold", percentile),
                ]
            )
            await CLIENT.post(
                url=quantile_rule_collection.url(self.host, self.port),
                content=quantile_rule_collection.post_data,
            )

        # send sum
        sum_and_count_rule_collection = _CSVRuleCollection.from_rules(
            [
                *item_rules,
                _CSVRule(
                    "metric",
                    "auction_price_gold_sum",
                    sum(auction.quantity * auction.price_gold for auction in auctions),
                ),
                _CSVRule("metric", "auction_price_gold_count", total_items),
            ]
        )
        await CLIENT.post(
            url=sum_and_count_rule_collection.url(self.host, self.port),
            content=sum_and_count_rule_collection.post_data,
        )

        # TODO delete this, just for debug
        print(f"{auctions[0].item.name} ({total_items:,}x): {percentiles}")

    async def export_auction_min(self, auctions: list[Auction]) -> None:
        rule_collection = _CSVRuleCollection.from_rules(
            [
                *self._label_rules_for_item(auctions[0].item),
                _CSVRule(
                    "metric",
                    "auction_price_gold_min",
                    min(auction.price_gold for auction in auctions),
                ),
            ]
        )
        await CLIENT.post(
            url=rule_collection.url(self.host, self.port),
            content=rule_collection.post_data,
        )
