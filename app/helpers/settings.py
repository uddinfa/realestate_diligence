import os
from dotenv import load_dotenv

load_dotenv()

NYC_GEOCLIENT_URL = os.getenv("NYC_GEOCLIENT_URL", "https://api.nyc.gov/geoclient/v2")
NYC_GEOCLIENT_SUBSCRIPTION_KEY = os.getenv("NYC_GEOCLIENT_SUBSCRIPTION_KEY")

SOCRATA_APP_TOKEN = os.getenv("SOCRATA_APP_TOKEN")
RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY")

if not NYC_GEOCLIENT_SUBSCRIPTION_KEY:
    print("Geoclient key not set. Demo will still run but BBL lookups may be limited.")
if not SOCRATA_APP_TOKEN:
    print("Set SOCRATA_APP_TOKEN for higher NYC Open Data rate limits.")
