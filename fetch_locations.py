#!/usr/bin/env python3
"""
Fetch location data (lat/lon) for US telecom and internet providers.
Uses GET /slugs/{slug}/locations with last 7 days date range.
Geocoding options:
  - ZCTA (default): lat/lon→ZIP via Census shapefile, then ZIP→city/state via CSV lookup. Fast.
  - Nominatim (--nominatim): lat/lon→zip,city,state via Nominatim. Slow (~1 req/sec).
Saves to Downloads folder on local machine.
"""

import os
import sys
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import requests
from dotenv import load_dotenv
from geopy.geocoders import Nominatim
from geopy.extra.rate_limiter import RateLimiter

load_dotenv()

# ZIP centroid CSV with lat/lng, city, state (~5MB, used for fast geocoding)
ZIP_LOOKUP_URL = "https://raw.githubusercontent.com/akinniyi/US-Zip-Codes-With-City-State/master/uszips.csv"
ZCTA_CACHE_DIR = os.path.join(os.path.expanduser("~"), ".cache", "lms-fetch-zip")

BASE_URL = "https://downdetectorapi.com/v2"

ALL_PROVIDER_SLUGS = [
    "verizon", "att", "t-mobile", "us-cellular", "visible", "straight-talk",
    "spectrum", "xfinity", "comcast", "cox", "mediacom", "optimum", "rcn",
    "centurylink", "frontier", "windstream", "tds-telecom", "astound", "wow",
    "kinetic", "starlink", "google-fiber", "dish-network",
]
US_PROVIDER_SLUGS = [  # default subset; use ALL_PROVIDER_SLUGS for full list
    "t-mobile",
    "us-cellular",
    "visible",
    "straight-talk",
    "spectrum",
    "xfinity",
    "comcast",
    "cox",
    "mediacom",
    "optimum",
    "rcn",
    "centurylink",
    "frontier",
    #"windstream",
    "tds-telecom",
    "astound",
    "wow",
    "kinetic",
    "starlink",
    "google-fiber",
    "dish-network",
]


def get_headers() -> dict:
    token = os.getenv("DOWNDETECTOR_BEARER_TOKEN")
    if not token:
        raise ValueError("DOWNDETECTOR_BEARER_TOKEN not set in .env")
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
    }


def get_us_country_id() -> Optional[int]:
    """Fetch US country_id from API."""
    try:
        resp = requests.get(f"{BASE_URL}/countries/US", headers=get_headers(), timeout=30)
        if resp.status_code == 200:
            data = resp.json()
            return data.get("downdetector_id") or data.get("id")
    except Exception:
        pass
    return 89  # fallback if API lookup fails


def _get_date_range(days: int = 7) -> tuple:
    """Return (start_str, end_str) for last N days (inclusive)."""
    now = datetime.utcnow()
    end = now.replace(hour=23, minute=59, second=59, microsecond=0)
    start = (end - timedelta(days=max(1, days) - 1)).replace(hour=0, minute=0, second=0, microsecond=0)
    return start.strftime("%Y-%m-%dT00:00:00+00:00"), end.strftime("%Y-%m-%dT23:59:59+00:00")


def _extract_address_components(raw: dict) -> Dict[str, str]:
    """Extract zip, city, state from Nominatim address dict."""
    addr = raw.get("address", {}) if isinstance(raw, dict) else {}
    zip_code = addr.get("postcode") or addr.get("zip") or ""
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


def _geocode_rows_centroid(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Assign ZIP, city, state by finding the nearest ZIP centroid (haversine).

    Uses the lightweight uszips.csv (~5MB) instead of the 150MB Census shapefile.
    No geopandas/GDAL required — only numpy (bundled with pandas).
    """
    csv_path = _get_zip_lookup_path()
    df = pd.read_csv(csv_path)

    lat_col = "lat" if "lat" in df.columns else df.columns[0]
    lng_col = "lng" if "lng" in df.columns else df.columns[1]
    zip_col = "zip" if "zip" in df.columns else df.columns[2]
    city_col = "city" if "city" in df.columns else None
    state_col = "state_id" if "state_id" in df.columns else ("state_name" if "state_name" in df.columns else "state")

    zip_lats = df[lat_col].values.astype(float)
    zip_lons = df[lng_col].values.astype(float)
    zip_codes = df[zip_col].astype(str).values
    zip_cities = df[city_col].astype(str).values if city_col else np.full(len(df), "")
    zip_states = df[state_col].astype(str).values

    zip_lats_rad = np.radians(zip_lats)
    zip_lons_rad = np.radians(zip_lons)
    cos_zip_lats = np.cos(zip_lats_rad)

    cache: Dict[Tuple[float, float], Dict[str, str]] = {}

    for r in rows:
        lat, lon = r.get("latitude"), r.get("longitude")
        try:
            lat_f, lon_f = float(lat), float(lon)
            if pd.isna(lat_f) or pd.isna(lon_f):
                raise ValueError
        except (TypeError, ValueError):
            r["zip"] = r["city"] = r["state"] = ""
            continue

        key = (round(lat_f, 4), round(lon_f, 4))
        if key not in cache:
            lat_rad = np.radians(lat_f)
            lon_rad = np.radians(lon_f)
            dlat = zip_lats_rad - lat_rad
            dlon = zip_lons_rad - lon_rad
            a = np.sin(dlat / 2) ** 2 + np.cos(lat_rad) * cos_zip_lats * np.sin(dlon / 2) ** 2
            dist = np.arcsin(np.sqrt(np.minimum(a, 1.0)))
            idx = int(np.argmin(dist))
            cache[key] = {"zip": zip_codes[idx], "city": zip_cities[idx], "state": zip_states[idx]}

        match = cache[key]
        r["zip"] = match["zip"]
        r["city"] = match["city"]
        r["state"] = match["state"]

    unique_zips = len({r["zip"] for r in rows if r.get("zip")})
    print(f"  Matched {len(cache)} unique coordinates to {unique_zips} unique ZIPs")
    return rows


def _get_zip_lookup_path() -> str:
    """Download ZIP→city/state CSV if needed. Returns path to CSV file."""
    os.makedirs(ZCTA_CACHE_DIR, exist_ok=True)
    csv_path = os.path.join(ZCTA_CACHE_DIR, "uszips.csv")
    if os.path.exists(csv_path):
        return csv_path
    print("Downloading ZIP→city/state lookup (~5MB, one-time)...")
    resp = requests.get(ZIP_LOOKUP_URL, timeout=60)
    resp.raise_for_status()
    with open(csv_path, "wb") as f:
        f.write(resp.content)
    print(f"Saved to {csv_path}")
    return csv_path


def _lookup_city_state_from_zip(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Look up city and state from ZIP using cached CSV (ZCTA output → city/state enrichment)."""
    unique_zips = {str(r.get("zip", "")).strip() for r in rows if r.get("zip")}
    unique_zips = {z for z in unique_zips if z}

    if not unique_zips:
        return rows

    csv_path = _get_zip_lookup_path()
    df = pd.read_csv(csv_path)
    # uszips.csv columns: zip, city, state_id (2-letter abbr), state_name
    zip_col = "zip" if "zip" in df.columns else df.columns[0]
    city_col = "city" if "city" in df.columns else None
    state_col = "state_id" if "state_id" in df.columns else ("state_name" if "state_name" in df.columns else "state")

    zip_to_place: Dict[str, Dict[str, str]] = {}
    if "population" in df.columns:
        df_sorted = df.sort_values("population", ascending=False)
    else:
        df_sorted = df
    for _, row in df_sorted.iterrows():
        z = str(row.get(zip_col, "")).strip()
        if z and z not in zip_to_place:
            city = str(row.get(city_col, "")).strip() if city_col else ""
            state_val = str(row.get(state_col, "")).strip()
            zip_to_place[z] = {"city": city, "state": state_val}
    for z in unique_zips:
        zip_to_place.setdefault(z, {"city": "", "state": ""})

    for r in rows:
        z = str(r.get("zip", "")).strip()
        place = zip_to_place.get(z, {"city": "", "state": ""})
        r["city"] = place.get("city", "")
        r["state"] = place.get("state", "")

    print(f"  Filled city/state for {len(unique_zips)} unique ZIP(s) via CSV lookup")
    return rows


def _geocode_rows(rows: List[Dict[str, Any]], delay: float = 1.1) -> Tuple[List[Dict[str, Any]], bool]:
    """Reverse geocode lat/lon to zip, city, state. Returns (rows, interrupted). On Ctrl+C saves partial and exits."""
    geolocator = Nominatim(user_agent="fetch-locations-geocode")
    reverse = RateLimiter(geolocator.reverse, min_delay_seconds=delay)

    coord_key = lambda lat, lon: (round(float(lat), 4), round(float(lon), 4))
    cache: Dict[Tuple[float, float], Dict[str, str]] = {}

    def lookup(lat: Any, lon: Any) -> Dict[str, str]:
        try:
            lat_f, lon_f = float(lat), float(lon)
            if lat_f != lat_f or lon_f != lon_f:
                return {"zip": "", "city": "", "state": ""}
        except (TypeError, ValueError):
            return {"zip": "", "city": "", "state": ""}
        key = coord_key(lat_f, lon_f)
        if key not in cache:
            try:
                loc = reverse(f"{lat_f}, {lon_f}")
                if loc and loc.raw:
                    cache[key] = _extract_address_components(loc.raw)
                else:
                    cache[key] = {"zip": "", "city": "", "state": ""}
            except Exception:
                cache[key] = {"zip": "", "city": "", "state": ""}
        return cache[key]

    unique_count = len({coord_key(r.get("latitude"), r.get("longitude")) for r in rows if r.get("latitude") is not None and r.get("longitude") is not None})
    print(f"\nGeocoding {unique_count} unique coordinates (Nominatim, ~1 req/sec). Press Ctrl+C to save partial and exit.")

    result = []
    try:
        for i, row in enumerate(rows):
            r = dict(row)
            addr = lookup(r.get("latitude"), r.get("longitude"))
            r["zip"] = addr["zip"]
            r["city"] = addr["city"]
            r["state"] = addr["state"]
            result.append(r)
            if (i + 1) % 1000 == 0:
                print(f"  Processed {i + 1}/{len(rows)} rows...")
        return result, False
    except KeyboardInterrupt:
        print("\n\nInterrupted. Adding remaining rows without geocoding...")
        for j in range(len(result), len(rows)):
            r = dict(rows[j])
            r["zip"] = ""
            r["city"] = ""
            r["state"] = ""
            result.append(r)
        return result, True


def _fetch_indicator_name(indicator_id: Any) -> str:
    """Fetch indicator name from Downdetector API. Returns empty string on error."""
    try:
        bid = int(float(indicator_id))
    except (TypeError, ValueError):
        return ""
    try:
        resp = requests.get(f"{BASE_URL}/indicators/{bid}", headers=get_headers(), timeout=10)
        if resp.status_code != 200:
            return ""
        d = resp.json()
        trans = d.get("translations") or {}
        return (trans.get("en") or d.get("slug") or "").strip() or ""
    except Exception:
        return ""


def _add_affected_service_column(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Add affected_service column by looking up indicator_id via Downdetector API."""
    unique_ids = set()
    for r in rows:
        v = r.get("indicator_id")
        if v is not None and not (isinstance(v, float) and pd.isna(v)):
            try:
                unique_ids.add(int(float(v)))
            except (TypeError, ValueError):
                pass
    id_to_name: Dict[int, str] = {}
    for iid in unique_ids:
        name = _fetch_indicator_name(iid)
        id_to_name[iid] = name if name else f"indicator_{iid}"
    for r in rows:
        v = r.get("indicator_id")
        try:
            bid = int(float(v)) if v is not None and not (isinstance(v, float) and pd.isna(v)) else None
        except (TypeError, ValueError):
            bid = None
        r["affected_service"] = id_to_name.get(bid, "") if bid is not None else ""
    print(f"  Resolved {len(id_to_name)} indicator(s) to service names")
    return rows


def _has_valid_indicator_id(row: Dict[str, Any]) -> bool:
    """Return True if row has a valid (non-null, non-empty) indicator_id."""
    val = row.get("indicator_id")
    if val is None:
        return False
    if isinstance(val, float) and (pd.isna(val) or val == 0):
        return False
    if isinstance(val, str) and val.strip() == "":
        return False
    if isinstance(val, (int, float)) and val == 0:
        return False
    return True


def _flatten_location_record(record: Dict[str, Any], slug: str) -> Dict[str, Any]:
    """Flatten nested location/network structure for CSV."""
    flat: Dict[str, Any] = {
        "provider": slug,
        "company_id": record.get("company_id"),
        "created_at": record.get("created_at"),
        "device": record.get("device"),
        "indicator_id": record.get("indicator_id"),
    }
    loc = record.get("location") or {}
    flat["latitude"] = loc.get("latitude")
    flat["longitude"] = loc.get("longitude")
    flat["city_id"] = loc.get("city_id")
    flat["country_id"] = loc.get("country_id")
    flat["source"] = loc.get("source")
    net = record.get("network") or {}
    flat["asn"] = net.get("asn")
    flat["provider_id"] = net.get("provider_id")
    return flat


def fetch_locations_for_slug(
    slug: str,
    start_str: str,
    end_str: str,
    country_id: int,
    page_size: int = 1000,
) -> List[Dict[str, Any]]:
    """Fetch locations for one slug with pagination. Returns flattened records."""
    url = f"{BASE_URL}/slugs/{slug}/locations"
    all_records: List[Dict[str, Any]] = []
    page_token: Optional[str] = None

    try:
        while True:
            params = {
                "startdate": start_str,
                "enddate": end_str,
                "countries": country_id,
                "page_size": page_size,
            }
            if page_token:
                params["page"] = page_token
            resp = requests.get(url, params=params, headers=get_headers(), timeout=30)
            if resp.status_code != 200:
                break
            data = resp.json()
            records = data if isinstance(data, list) else (data.get("data", []) or [])
            for r in records:
                if isinstance(r, dict):
                    all_records.append(_flatten_location_record(r, slug))
            next_token = resp.headers.get("x-page-next") or resp.headers.get("X-Page-Next")
            if not next_token:
                break
            page_token = next_token
    except Exception:
        pass

    return all_records


def _get_download_path() -> str:
    """Return path to save CSV in Downloads folder."""
    downloads = os.path.join(os.path.expanduser("~"), "Downloads")
    os.makedirs(downloads, exist_ok=True)
    return os.path.join(downloads, "us_providers_locations.csv")


def fetch_all_locations(
    slugs: Optional[List[str]] = None,
    output: Optional[str] = None,
    geocode: bool = True,
    use_zcta: bool = True,
    include_no_indicator: bool = False,
    days: int = 7,
) -> None:
    """Fetch locations for all US providers and save to CSV. Add zip via ZCTA (fast) then city/state via CSV lookup; or use Nominatim for full geocoding (slow)."""
    slugs = slugs or US_PROVIDER_SLUGS
    output_path = output if output is not None else _get_download_path()

    start_str, end_str = _get_date_range(days)
    country_id = get_us_country_id()

    print(f"Fetching locations for {len(slugs)} US providers (last {days} days)")
    print(f"  startdate: {start_str}")
    print(f"  enddate:   {end_str}")
    print(f"  country_id (US): {country_id}")
    print()

    all_rows: List[Dict[str, Any]] = []
    for slug in slugs:
        records = fetch_locations_for_slug(slug, start_str, end_str, country_id)
        if records:
            all_rows.extend(records)
            print(f"  {slug}: {len(records)} location(s)")
        else:
            print(f"  {slug}: no data")

    if not all_rows:
        print("\nNo location records retrieved. Check API credentials or date range.")
        return

    # Optionally filter out rows without valid indicator_id
    if not include_no_indicator:
        before = len(all_rows)
        all_rows = [r for r in all_rows if _has_valid_indicator_id(r)]
        dropped = before - len(all_rows)
        if dropped > 0:
            print(f"\nFiltered to records with valid indicator_id ({dropped} without indicator_id excluded)")
    else:
        print("\nIncluding all records (including rows with empty indicator_id)")

    if not all_rows:
        print("No records to save.")
        return

    if geocode:
        if use_zcta:
            print("\nAdding ZIP, city, state via centroid matching (fast)...")
            all_rows = _geocode_rows_centroid(all_rows)
        else:
            print("\nAdding zip, city, state via Nominatim (slow, ~1 req/sec)...")
            all_rows, interrupted = _geocode_rows(all_rows)
            if interrupted:
                print("Partial results (geocoding stopped by user).")
    else:
        for r in all_rows:
            r["zip"] = ""
            r["city"] = ""
            r["state"] = ""

    print("Resolving indicator_id to affected service names...")
    all_rows = _add_affected_service_column(all_rows)

    df = pd.DataFrame(all_rows)
    # Order affected_service right after indicator_id
    cols = list(df.columns)
    if "affected_service" in cols and "indicator_id" in cols:
        cols.remove("affected_service")
        idx = cols.index("indicator_id") + 1
        cols.insert(idx, "affected_service")
        df = df[cols]
    df.to_csv(output_path, index=False)
    print(f"\nSaved {len(all_rows)} total records to: {output_path}")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Fetch Downdetector locations for US providers")
    parser.add_argument("-o", "--output", help="Output CSV path (default: Downloads folder)")
    parser.add_argument("--no-geocode", action="store_true", help="Skip geocoding (no zip/city/state)")
    parser.add_argument("--nominatim", action="store_true", help="Use Nominatim instead of ZCTA (slow, adds city/state)")
    parser.add_argument("--include-no-indicator", action="store_true", help="Include rows with empty indicator_id (default: exclude them)")
    parser.add_argument("--days", type=int, default=7, help="Number of days to fetch (default: 7)")
    args = parser.parse_args()
    fetch_all_locations(output=args.output, geocode=not args.no_geocode, use_zcta=not args.nominatim, include_no_indicator=args.include_no_indicator, days=args.days)
