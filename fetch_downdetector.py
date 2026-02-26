#!/usr/bin/env python3
"""
Fetch events data from the Downdetector API and save to CSV.
Uses Bearer token from .env for authentication.
"""

import argparse
import os
import sys
from pathlib import Path
from typing import Optional

import pandas as pd
import requests
from dotenv import load_dotenv

load_dotenv()

BASE_URL = "https://downdetectorapi.com/v2"


def get_headers() -> dict:
    """Build auth headers from environment."""
    token = os.getenv("DOWNDETECTOR_BEARER_TOKEN")
    if not token:
        raise ValueError(
            "DOWNDETECTOR_BEARER_TOKEN not set. Add it to .env or set the environment variable."
        )
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }


def search_companies(name: str) -> list[dict]:
    """Search for companies by name. Returns list of company objects."""
    url = f"{BASE_URL}/companies/search"
    params = {
        "fields": "id,name,slug,country_iso,indicators,site_id",
        "name": name,
    }
    resp = requests.get(url, params=params, headers=get_headers(), timeout=30)
    resp.raise_for_status()
    data = resp.json()
    return data if isinstance(data, list) else [data]


def fetch_company_events(company_id: int, page_token: Optional[str] = None) -> tuple:
    """
    Fetch events for a company. Returns (events_list, next_page_token).
    """
    url = f"{BASE_URL}/companies/{company_id}/events"
    params = {}
    if page_token:
        params["page"] = page_token

    resp = requests.get(url, params=params if params else None, headers=get_headers(), timeout=30)
    resp.raise_for_status()
    data = resp.json()

    # Handle various response shapes
    if isinstance(data, list):
        events = data
    elif isinstance(data, dict):
        events = data.get("data", data.get("events", data.get("items", [])))
        if not isinstance(events, list):
            events = [data]
    else:
        events = []

    next_token = resp.headers.get("x-page-next") or resp.headers.get("X-Page-Next")
    return events, (next_token if next_token else None)


def fetch_all_events(company_id: int) -> list[dict]:
    """Fetch all events, following pagination."""
    all_events = []
    page_token = None

    while True:
        events, next_token = fetch_company_events(company_id, page_token)
        all_events.extend(events)
        if not next_token:
            break
        page_token = next_token

    return all_events


def _has_valid_indicator_id(row) -> bool:
    """Return True if row has a valid (non-null, non-empty) indicator_id."""
    val = row.get("indicator_id") if "indicator_id" in row.index else None
    if val is None or pd.isna(val):
        return False
    if isinstance(val, str) and val.strip() == "":
        return False
    if isinstance(val, (int, float)) and val == 0:
        return False
    return True


def flatten_to_dataframe(events: list[dict]) -> pd.DataFrame:
    """Convert events (possibly nested) to a flat DataFrame."""
    if not events:
        return pd.DataFrame()

    try:
        df = pd.json_normalize(events)
    except Exception:
        df = pd.DataFrame(events)

    # Ensure indicator_id column (may be nested as indicator.id)
    if "indicator_id" not in df.columns and "indicator.id" in df.columns:
        df["indicator_id"] = df["indicator.id"]
    if "indicator_id" not in df.columns:
        df["indicator_id"] = None

    # Keep only records with valid indicator_id
    before = len(df)
    df = df[df.apply(_has_valid_indicator_id, axis=1)].reset_index(drop=True)
    dropped = before - len(df)
    if dropped > 0:
        print(f"Filtered out {dropped} record(s) without valid indicator_id")

    return df


def main():
    parser = argparse.ArgumentParser(
        description="Fetch Downdetector API events and save to CSV."
    )
    parser.add_argument(
        "company",
        help="Company ID (integer) or company name to search for",
    )
    parser.add_argument(
        "-o", "--output",
        default="downdetector_events.csv",
        help="Output CSV path (default: downdetector_events.csv)",
    )
    parser.add_argument(
        "--search",
        action="store_true",
        help="Treat company as a name and search first; use first match",
    )

    args = parser.parse_args()

    company_id = None

    if args.search or not args.company.isdigit():
        # Search by name
        print(f"Searching for company: {args.company}")
        companies = search_companies(args.company)
        if not companies:
            print("No companies found.", file=sys.stderr)
            sys.exit(1)
        company_id = companies[0]["id"]
        print(f"Using company: {companies[0].get('name', 'Unknown')} (id={company_id})")
    else:
        company_id = int(args.company)

    print(f"Fetching events for company_id={company_id}...")
    events = fetch_all_events(company_id)
    print(f"Fetched {len(events)} event(s)")

    df = flatten_to_dataframe(events)
    out_path = Path(args.output)
    df.to_csv(out_path, index=False)
    print(f"Saved to: {out_path}")


if __name__ == "__main__":
    main()
