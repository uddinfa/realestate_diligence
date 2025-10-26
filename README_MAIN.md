# Real Estate Due Diligence Demo

This repo shows a public demo of a due diligence pipeline for NYC residential buyers / cash investors:
- **Geoclient v2** → get BBL from address (header auth)
- **PLUTO (Socrata)** → property facts (building class, units, FAR, zoning, year built)

> A `.env.example` is provided.

## Quickstart
```bash
python3 -m venv .venv && source .venv/bin/activate
pip3 install -r requirements.txt

cp .env.example .env
# edit .env and paste your Geoclient subscription key

python3 -m app.cli --address "145-47 157 Street, Jamaica, NY 11434"
