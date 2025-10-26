import re
import requests
from app.utils.config import NYC_GEOCLIENT_URL, NYC_GEOCLIENT_SUBSCRIPTION_KEY

class NYCGeocoder:
    def __init__(self):
        self.base_url = NYC_GEOCLIENT_URL.rstrip("/")
        self.headers = {
            "Ocp-Apim-Subscription-Key": NYC_GEOCLIENT_SUBSCRIPTION_KEY,
            "Cache-Control": "no-cache",
        }

    def _parse_address(self, address: str):
        addr = re.sub(r",", " ", address)
        addr = re.sub(r"\s+", " ", addr).strip()

        # detect borough
        boroughs = ["manhattan", "bronx", "brooklyn", "queens", "staten"]
        borough = next((b for b in boroughs if b in addr.lower()), "queens").title()

        # remove NY + ZIP
        addr = re.sub(r"\b(NY|New York)\b", "", addr, flags=re.I)
        addr = re.sub(r"\b\d{5}\b", "", addr)

        tokens = addr.split()
        house = next((t for t in tokens if re.match(r"^\d", t)), "")
        remaining = [t for t in tokens if t != house and t.lower() not in boroughs + ["ny", "new", "york"]]
        street = " ".join(remaining).strip()

        # normalize ordinal
        street = re.sub(r"(\d+)(st|nd|rd|th)\b", r"\1", street, flags=re.I)
        return house, street, borough

    def bbl_lookup(self, address: str) -> dict:
        if not NYC_GEOCLIENT_SUBSCRIPTION_KEY:
            return {}
        house, street, borough = self._parse_address(address)
        url = f"{self.base_url}/address"
        params = {"houseNumber": house, "street": street, "borough": borough}

        resp = requests.get(url, params=params, headers=self.headers, timeout=15)
        resp.raise_for_status()
        data = resp.json().get("address", {})

        # v2 fields + fallbacks
        full_bbl = data.get("bbl")
        boro = data.get("bblBoroughCode") or (full_bbl or "")[:1]
        block = data.get("bblTaxBlock") or data.get("bblBlock") or (full_bbl or "")[1:6]
        lot = data.get("bblTaxLot") or data.get("bblLot") or (full_bbl or "")[6:]

        if all([boro, block, lot]):
            return {"borough": boro, "block": block, "lot": lot, "bbl": f"{boro}{block}{lot}"}
        return {}
