"""
Backup Grafana dashboards from the live Grafana server to JSON files in at
grafana/dashboards.

(If the Grafana volume is somehow deleted, Grafana is set up to provision new dashboards
from these the JSON files.)

Warning: All files in grafana/dashboards will be first deleted. This is to ensure that
old dashboards are culled from the repo.
"""

import json
from collections.abc import Iterable
from pathlib import Path

import httpx

CLIENT = httpx.Client()

DASHBOARD_PATH = Path(__file__).parent.parent / "grafana" / "dashboards"

# published port for grafana
GRAFANA_ROOT_URL = "http://localhost:3000/"
DASHBOARD_SEARCH_URL = f"{GRAFANA_ROOT_URL}api/search"


def dashboard_url(uid: str) -> str:
    return f"{GRAFANA_ROOT_URL}api/dashboards/uid/{uid}"


def get_dashboard_uids() -> Iterable[str]:
    response = CLIENT.get(DASHBOARD_SEARCH_URL)
    response.raise_for_status()

    for obj in response.json():
        yield obj["uid"]


def write_dashboard(uid: str) -> Path:
    dashboard_path = DASHBOARD_PATH / f"{uid}.json"

    response = CLIENT.get(dashboard_url(uid))
    response.raise_for_status()

    dashboard_json = response.json()['dashboard']
    dashboard_path.write_text(json.dumps(dashboard_json, indent=2))

    return dashboard_path


def backup_dashboards() -> None:
    # first, remove any files currently in the dashboard dir, so we only keep an current
    # set
    for path in DASHBOARD_PATH.iterdir():
        if path.is_file():
            path.unlink()

    # then, download all the current dashboards
    for uid in get_dashboard_uids():
        dashboard_path = write_dashboard(uid)
        print(f"wrote {uid} to {dashboard_path}")


if __name__ == "__main__":
    backup_dashboards()
