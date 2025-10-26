
```python
from app.services.geocode_service import NYCGeocoder

def test_parse_only():
    geo = NYCGeocoder()
    # this won't hit API in CI unless you set a key; just ensures class imports
    assert hasattr(geo, "bbl_lookup")
