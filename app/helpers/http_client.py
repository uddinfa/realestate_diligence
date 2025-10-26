import requests

DEFAULT_TIMEOUT = 15

def get_json(url, params=None, headers=None, timeout=DEFAULT_TIMEOUT):
    h = {"Accept": "application/json", **(headers or {})}
    r = requests.get(url, params=params, headers=h, timeout=timeout)
    r.raise_for_status()
    return r.json()
