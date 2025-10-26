import requests
from app.utils.config import SOCRATA_APP_TOKEN

PLUTO_ENDPOINT = "https://data.cityofnewyork.us/resource/64uk-42ks.json"

def get_pluto_by_bbl(bbl: str) -> dict:
    if not bbl:
        return {}
    headers = {"Accept": "application/json"}
    if SOCRATA_APP_TOKEN:
        headers["X-App-Token"] = SOCRATA_APP_TOKEN
    resp = requests.get(PLUTO_ENDPOINT, params={"bbl": bbl}, headers=headers, timeout=20)
    resp.raise_for_status()
    rows = resp.json()
    return rows[0] if rows else {}
