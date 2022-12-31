import csv
import io

from attrs import frozen
from yarl import URL

from wowauction.auction import Auction
from wowauction.http_client import CLIENT


@frozen
class VMAgentAPI:
    host: str
    port: int

    async def export(self, auction: Auction) -> None:
        """
        The URL and data for importing into VictoriaMetrics,
        https://docs.victoriametrics.com/Single-server-VictoriaMetrics.html#how-to-import-csv-data
        """
        data = [
            auction.item.id_,  # 1
            auction.item.name,  # 2
            auction.item.quality, # 3
            auction.item.rank, # 4
            auction.item.major,  # 5
            auction.item.minor,  # 6
            auction.item.patch,  # 7
            auction.item.build,  # 8
            auction.price_gold,  # 9
            auction.quantity,  # 10
            auction.time_left_num,  # 11
            int(auction.timestamp),  # 12
        ]
        csv_output = io.StringIO()
        csv_writer = csv.writer(csv_output)
        csv_writer.writerow(data)
        data_string = csv_output.getvalue()
        csv_output.close()

        rules = [
            "1:label:id",
            "2:label:name",
            "3:label:quality",
            "4:label:rank",
            "5:label:major",
            "6:label:minor",
            "7:label:patch",
            "8:label:build",
            "9:metric:price_gold",
            "10:metric:quantity",
            "11:metric:time_left",
            "12:time:unix_s",
        ]

        url = str(
            URL.build(
                scheme="http",
                host=self.host,
                port=self.port,
                path="/api/v1/import/csv",
                query={"format": ",".join(rules)},
            )
        )

        await CLIENT.post(url=url, content=data_string)
