import argparse
from app.services.geocode_service import NYCGeocoder
from app.services.pluto_service import get_pluto_by_bbl

def summarize(pluto: dict) -> dict:
    if not pluto:
        return {}
    return {
        "Building Class": pluto.get("bldgclass"),
        "Land Use": pluto.get("landuse"),
        "Year Built": pluto.get("yearbuilt"),
        "Stories": pluto.get("numfloors"),
        "Residential Units": pluto.get("unitsres"),
        "Lot Area (sqft)": pluto.get("lotarea"),
        "Building Area (sqft)": pluto.get("bldgarea"),
        "Zoning": " / ".join(filter(None, [
            pluto.get("zoningdist1"), pluto.get("zoningdist2"),
            pluto.get("zoningdist3"), pluto.get("zoningdist4")
        ])) or None,
        "Built FAR": pluto.get("builtfar"),
        "Max FAR": pluto.get("maxfar"),
        "Neighborhood (NTA)": pluto.get("nta"),
        "School District": pluto.get("schooldist"),
        "Condo #": pluto.get("condono"),
        "Owner (masked)": (pluto.get("ownername")[:2] + "***") if pluto.get("ownername") else None,
    }

def main():
    parser = argparse.ArgumentParser(description="NYC Due Diligence Demo (public data only)")
    parser.add_argument("--address", required=True, help="e.g., '145-47 157 Street, Jamaica, NY 11434'")
    args = parser.parse_args()

    geo = NYCGeocoder()
    gid = geo.bbl_lookup(args.address)
    if not gid:
        print("BBL not found via Geoclient (check key) — cannot fetch PLUTO.")
        return

    print(f"BBL: {gid['bbl']}  (Boro={gid['borough']}, Block={gid['block']}, Lot={gid['lot']})")
    pluto = get_pluto_by_bbl(gid["bbl"])
    summary = summarize(pluto)

    print("\nPLUTO summary:")
    if not summary:
        print(" - No PLUTO record found.")
    for k, v in summary.items():
        print(f" - {k}: {v}")

if __name__ == "__main__":
    main()
