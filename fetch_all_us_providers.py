#!/usr/bin/env python3
"""
Fetch aggregated report counts for all US telecom and internet providers.
Uses a fixed slug list. Combines results into a single CSV with a provider column.
"""

import os
import sys
from datetime import datetime, timedelta
from typing import List, Optional

import pandas as pd
import requests
from dotenv import load_dotenv

load_dotenv()

BASE_URL = "https://downdetectorapi.com/v2"

# Fixed list of US telecom and internet provider slugs (Downdetector US site)
US_PROVIDER_SLUGS = [
    # Mobile carriers
    "verizon",
    "att",
    "t-mobile",
    "us-cellular",
    "visible",
    "straight-talk",
    # Cable / broadband
    "spectrum",
    "xfinity",
    "comcast",
    "cox",
    "mediacom",
    "optimum",
    "rcn",
    # Regional / other
    "centurylink",
    "frontier",
    "windstream",
    "tds-telecom",
    "astound",
    "wow",
    "kinetic",
    # Satellite / fiber
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


def fetch_reports_for_slug(slug: str, start_str: str, end_str: str, interval: str = "1h") -> list:
    """Fetch reports for one slug. Returns list of records or empty list on error."""
    url = f"{BASE_URL}/slugs/{slug}/reports"
    params = {"startdate": start_str, "enddate": end_str, "interval": interval}
    try:
        resp = requests.get(url, params=params, headers=get_headers(), timeout=30)
        if resp.status_code != 200:
            return []
        data = resp.json()
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            return [data]
        return []
    except Exception:
        return []


def _get_last_7_days_range():
    """Return (start_str, end_str) for last 7 days: from 7 days ago 00:00 UTC to current day 23:59 UTC."""
    now = datetime.utcnow()
    end = now.replace(hour=23, minute=59, second=59, microsecond=0)
    start = (end - timedelta(days=6)).replace(hour=0, minute=0, second=0, microsecond=0)
    return start.strftime("%Y-%m-%dT00:00:00+00:00"), end.strftime("%Y-%m-%dT23:59:59+00:00")


def _get_download_path() -> str:
    """Return path to save CSV on this device (Downloads folder)."""
    downloads = os.path.join(os.path.expanduser("~"), "Downloads")
    os.makedirs(downloads, exist_ok=True)
    return os.path.join(downloads, "us_providers_reports.csv")


def fetch_all_providers(
    slugs: Optional[List[str]] = None,
    output: Optional[str] = None,
    interval: str = "1h",
) -> None:
    """Fetch reports for all US providers and save to CSV. Always uses last 7 days up to current day. Saves to Downloads folder on this device by default."""
    slugs = slugs or US_PROVIDER_SLUGS
    output_path = output if output is not None else _get_download_path()

    start_str, end_str = _get_last_7_days_range()

    print(f"Fetching reports for {len(slugs)} US providers (last 7 days)")
    print(f"  startdate: {start_str}")
    print(f"  enddate:   {end_str}")
    print(f"  interval:  {interval}")
    print()

    all_rows = []
    for slug in slugs:
        records = fetch_reports_for_slug(slug, start_str, end_str, interval)
        if records:
            for r in records:
                row = dict(r) if isinstance(r, dict) else {"data": r}
                row["provider"] = slug
                all_rows.append(row)
            print(f"  {slug}: {len(records)} records")
        else:
            print(f"  {slug}: no data (may not exist on US site)")

    if not all_rows:
        print("\nNo records retrieved. Check slugs or API credentials.")
        return

    df = pd.json_normalize(all_rows)
    if "provider" not in df.columns:
        df["provider"] = [r.get("provider", "") for r in all_rows]
    df.to_csv(output_path, index=False)
    print(f"\nSaved {len(all_rows)} total records to: {output_path}")


if __name__ == "__main__":
    output_arg = sys.argv[1] if len(sys.argv) > 1 else None
    fetch_all_providers(output=output_arg)
