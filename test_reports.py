#!/usr/bin/env python3
"""
Test the Downdetector reports API endpoint.
Uses dates within the last 7 days (plan limit).
"""

import os
import sys
from datetime import datetime, timedelta

import pandas as pd
import requests
from dotenv import load_dotenv

load_dotenv()

BASE_URL = "https://downdetectorapi.com/v2"


def test_reports(slug: str = "vodafone", output: str = "downdetector_reports.csv") -> None:
    """Test GET /slugs/{slug}/reports with valid date range."""
    token = os.getenv("DOWNDETECTOR_BEARER_TOKEN")
    if not token:
        print("ERROR: DOWNDETECTOR_BEARER_TOKEN not set in .env")
        return

    # Use last 7 days (within plan limit)
    end = datetime.utcnow()
    start = end - timedelta(days=6)
    start_str = start.strftime("%Y-%m-%dT00:00:00+00:00")
    end_str = end.strftime("%Y-%m-%dT23:59:59+00:00")

    url = f"{BASE_URL}/slugs/{slug}/reports"
    params = {
        "startdate": start_str,
        "enddate": end_str,
        "interval": "1h",
    }
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
    }

    print(f"Testing: {url}")
    print(f"  startdate: {start_str}")
    print(f"  enddate:   {end_str}")
    print(f"  interval:  {params['interval']}")
    print()

    resp = requests.get(url, params=params, headers=headers, timeout=30)

    if resp.status_code == 200:
        data = resp.json()
        records = [data] if isinstance(data, dict) else (data if isinstance(data, list) else [])
        if not records:
            print("SUCCESS: No records to save")
            return
        try:
            df = pd.json_normalize(records)
        except Exception:
            df = pd.DataFrame(records)
        df.to_csv(output, index=False)
        print(f"SUCCESS: Got {len(records)} record(s)")
        print(f"Saved to: {output}")
    else:
        print(f"FAILED: {resp.status_code} {resp.reason}")
        try:
            err = resp.json()
            print("Response:", err)
        except Exception:
            print("Body:", resp.text[:500])


if __name__ == "__main__":
    output_path = sys.argv[1] if len(sys.argv) > 1 else "downdetector_reports.csv"
    test_reports("vodafone", output=output_path)
