# hello-world

A collection of Python apps built with Streamlit and geopy, covering basic calculations, date utilities, and reverse geocoding.

Leela Bijili | 01/31/2026

---

## Project Structure

```
hello-world/
├── app.py                       # Product Calculator (Streamlit)
├── date_app.py                  # Day of the Week Calculator (Streamlit)
├── geocode.py                   # Reverse Geocoder (CLI)
├── sample_locations.csv         # Sample input for geocode.py
├── sample_locations_geocoded.csv# Sample output from geocode.py
├── requirements.txt             # Python dependencies
├── PLAN.md                      # Project plan
├── venv/                        # Virtual environment (not committed)
└── README.md
```

---

## Prerequisites

- Python 3.9+
- pip

---

## Setup

```bash
# Create and activate a virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

---

## App 1: Product Calculator

**File:** `app.py`

A Streamlit app where the user enters two numbers and sees their product.

### Run

```bash
streamlit run app.py
```

Opens at `http://localhost:8501`.

---

## App 2: Day of the Week Calculator

**File:** `date_app.py`

A Streamlit app where the user picks a date and sees which day of the week that date falls on for the next 10 years. Handles Feb 29 in non-leap years gracefully.

### Run

```bash
streamlit run date_app.py
```

Opens at `http://localhost:8501`.

---

## App 3: Reverse Geocoder

**File:** `geocode.py`

A command-line script that reads a CSV file containing latitude/longitude data, reverse geocodes each row, and outputs a new CSV with zip, city, and state columns appended.

### Design Details

- **Geocoding service:** Nominatim (OpenStreetMap) via the `geopy` library -- free, no API key required.
- **Column auto-detection:** Automatically finds latitude and longitude columns by matching common names (latitude/lat, longitude/long/lon/lng), case-insensitive.
- **Rate limiting:** Requests are throttled to 1.1 seconds apart using `geopy.extra.rate_limiter.RateLimiter`, respecting Nominatim's usage policy.
- **Address extraction:** Extracts zip, city, and state from Nominatim's address components with fallback keys:
  - **City:** city, town, village, municipality, county, state_district
  - **State:** state, province, region, county
  - **Zip:** postcode, zip
- **Error handling:** Invalid coordinates, empty results, and API errors are handled per row without stopping the batch.

### Usage

```bash
# Basic usage (output: sample_locations_geocoded.csv)
python geocode.py sample_locations.csv

# Custom output file
python geocode.py sample_locations.csv -o output.csv

# Specify column names manually
python geocode.py data.csv --lat Latitude --lon Longitude

# Adjust request delay (seconds)
python geocode.py data.csv --delay 2.0
```

### CLI Arguments

| Argument | Required | Description |
|----------|----------|-------------|
| `input_file` | Yes | Input CSV with latitude and longitude columns |
| `-o`, `--output` | No | Output CSV path (default: `{input}_geocoded.csv`) |
| `--lat` | No | Latitude column name (auto-detected if omitted) |
| `--lon` | No | Longitude column name (auto-detected if omitted) |
| `--delay` | No | Delay between requests in seconds (default: 1.1) |

### Input Format

CSV with latitude and longitude columns:

```csv
latitude,longitude
40.7128,-74.0060
34.0522,-118.2437
41.8781,-87.6298
```

### Sample Output

```csv
latitude,longitude,zip,city,state
40.7128,-74.006,10000,New York,New York
34.0522,-118.2437,90012,Los Angeles,California
41.8781,-87.6298,60604,Chicago,Illinois
29.7604,-95.3698,77002,Houston,Texas
33.4484,-112.074,85003,Phoenix,Arizona
```

---

## Dependencies

| Package | Purpose |
|---------|---------|
| `streamlit` | Web UI framework for the calculator apps |
| `geopy` | Geocoding library (Nominatim provider) |
| `pandas` | CSV reading, data manipulation, output |
