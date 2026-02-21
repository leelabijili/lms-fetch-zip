#!/usr/bin/env python3
"""
Reverse geocode latitude/longitude data from a CSV file to get zip, city, state.
Outputs results to a new CSV file.
"""

import argparse
import sys
from pathlib import Path
from typing import Optional, Tuple

import pandas as pd
from geopy.geocoders import Nominatim
from geopy.extra.rate_limiter import RateLimiter


def find_lat_lon_columns(df: pd.DataFrame) -> Tuple[str, str]:
    """Detect latitude and longitude column names (case-insensitive)."""
    cols_lower = {c.lower(): c for c in df.columns}

    lat_names = ["latitude", "lat"]
    lon_names = ["longitude", "long", "lon", "lng"]

    lat_col = None
    for name in lat_names:
        if name in cols_lower:
            lat_col = cols_lower[name]
            break

    lon_col = None
    for name in lon_names:
        if name in cols_lower:
            lon_col = cols_lower[name]
            break

    if lat_col is None or lon_col is None:
        raise ValueError(
            "Could not find latitude/longitude columns. "
            "Expected names: latitude/lat, longitude/long/lon/lng"
        )
    return lat_col, lon_col


def extract_address_components(raw: dict) -> dict:
    """Extract zip, city, state from Nominatim address dict."""
    addr = raw.get("address", {}) if isinstance(raw, dict) else {}

    zip_code = (
        addr.get("postcode")
        or addr.get("zip")
        or ""
    )

    city = (
        addr.get("city")
        or addr.get("town")
        or addr.get("village")
        or addr.get("municipality")
        or addr.get("county")
        or addr.get("state_district")
        or ""
    )

    state = (
        addr.get("state")
        or addr.get("province")
        or addr.get("region")
        or addr.get("county")
        or ""
    )

    return {"zip": zip_code, "city": city, "state": state}


def reverse_geocode_file(
    input_path: str,
    output_path: Optional[str] = None,
    lat_col: Optional[str] = None,
    lon_col: Optional[str] = None,
    delay: float = 1.1,
) -> str:
    """
    Read CSV with lat/lon, reverse geocode, write output CSV with zip, city, state.
    Uses Nominatim (OpenStreetMap) - free, no API key. Respects 1 req/sec rate limit.
    """
    input_path = Path(input_path)
    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    df = pd.read_csv(input_path)

    if lat_col is None or lon_col is None:
        lat_col, lon_col = find_lat_lon_columns(df)

    geolocator = Nominatim(user_agent="geocode-script")
    reverse = RateLimiter(geolocator.reverse, min_delay_seconds=delay)

    results = []
    total = len(df)

    for i, row in df.iterrows():
        lat = row[lat_col]
        lon = row[lon_col]

        try:
            lat_f = float(lat)
            lon_f = float(lon)
        except (TypeError, ValueError):
            results.append({"zip": "", "city": "", "state": "", "error": "Invalid coordinates"})
            print(f"  Row {i + 1}/{total}: Skipped (invalid: {lat}, {lon})")
            continue

        try:
            location = reverse(f"{lat_f}, {lon_f}")
            if location and location.raw:
                comp = extract_address_components(location.raw)
                comp["error"] = ""
                results.append(comp)
                print(f"  Row {i + 1}/{total}: {comp['city']}, {comp['state']} {comp['zip']}")
            else:
                results.append({"zip": "", "city": "", "state": "", "error": "No result"})
                print(f"  Row {i + 1}/{total}: No result")
        except Exception as e:
            results.append({"zip": "", "city": "", "state": "", "error": str(e)})
            print(f"  Row {i + 1}/{total}: Error - {e}")

    result_df = pd.DataFrame(results)
    out_df = pd.concat([df, result_df[["zip", "city", "state"]]], axis=1)

    if output_path is None:
        output_path = input_path.parent / f"{input_path.stem}_geocoded{input_path.suffix}"
    else:
        output_path = Path(output_path)

    out_df.to_csv(output_path, index=False)
    return str(output_path)


def main():
    parser = argparse.ArgumentParser(
        description="Reverse geocode lat/lon from CSV to get zip, city, state."
    )
    parser.add_argument(
        "input_file",
        help="Input CSV file with latitude and longitude columns",
    )
    parser.add_argument(
        "-o", "--output",
        help="Output CSV file (default: input_geocoded.csv)",
    )
    parser.add_argument(
        "--lat",
        help="Name of latitude column (auto-detected if omitted)",
    )
    parser.add_argument(
        "--lon",
        help="Name of longitude column (auto-detected if omitted)",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=1.1,
        help="Delay between API requests in seconds (default: 1.1)",
    )

    args = parser.parse_args()

    print(f"Reading: {args.input_file}")
    print("Reverse geocoding (Nominatim/OpenStreetMap)...")

    try:
        out_path = reverse_geocode_file(
            args.input_file,
            output_path=args.output,
            lat_col=args.lat,
            lon_col=args.lon,
            delay=args.delay,
        )
        print(f"\nDone. Output saved to: {out_path}")
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
