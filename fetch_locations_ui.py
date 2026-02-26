#!/usr/bin/env python3
"""
Streamlit UI for running fetch_locations: choose days, providers, geocoding, and indicator options.
Supports Streamlit Community Cloud via secrets (DOWNDETECTOR_BEARER_TOKEN).
"""

import io
import os
from contextlib import redirect_stdout

import streamlit as st

# Inject Streamlit secrets into env for fetch_locations (required for Streamlit Cloud)
# Locally, no secrets.toml → use .env. On Cloud, secrets.toml provides the token.
try:
    token = st.secrets.get("DOWNDETECTOR_BEARER_TOKEN", "")
    if token:
        os.environ["DOWNDETECTOR_BEARER_TOKEN"] = token
except Exception:
    pass  # No secrets file locally; fetch_locations uses .env via load_dotenv

# Import fetch module (load_dotenv runs on import)
from fetch_locations import (
    ALL_PROVIDER_SLUGS,
    US_PROVIDER_SLUGS,
    fetch_all_locations,
    _get_download_path,
)

st.set_page_config(page_title="Service Interruptions by Location", page_icon="📍", layout="centered")
st.title("📍 Service Interruptions by Location")
st.caption("Fetch location data for US telecom/internet providers, geocode to ZIP/city/state, and resolve affected service names.")

# --- Options ---
st.subheader("Filter Options")

col1, col2 = st.columns(2)

with col1:
    days = st.number_input(
        "Last N days to fetch",
        min_value=1,
        max_value=90,
        value=7,
        help="Last N days of data (API limit: 7 days for locations).",
    )

with col2:
    output_path = st.text_input(
        "Output path",
        value=_get_download_path(),
        help="Edit to change where the CSV is saved. Default: Downloads folder.",
    )

# Providers
st.markdown("**Providers**")
providers_selection = st.multiselect(
    "Select providers to fetch",
    options=ALL_PROVIDER_SLUGS,
    default=US_PROVIDER_SLUGS,
    help="Select one or more providers.",
)
select_all_providers = st.checkbox("Select all providers", value=False)
if select_all_providers:
    providers_selection = ALL_PROVIDER_SLUGS.copy()

# Indicator filter
st.markdown("**Indicator filter**")
include_no_indicator = st.checkbox(
    "Include rows with empty indicator_id",
    value=False,
    help="By default, rows without indicator_id are excluded. Check to include them.",
)

# Geocoding
st.markdown("**Geocoding**")
geocode = st.checkbox("Add ZIP, city, and state", value=True, help="Geocode lat/lon to address.")
use_zcta = True
if geocode:
    use_zcta = st.radio(
        "Geocoding method",
        options=["ZCTA (fast)", "Nominatim (slow)"],
        index=0,
        horizontal=True,
        help="ZCTA: Census shapefile + ZIP lookup. Nominatim: ~1 req/sec per unique coordinate.",
    )
    use_zcta = use_zcta.startswith("ZCTA")

# --- Run ---
st.divider()
run_clicked = st.button("Run fetch", type="primary", use_container_width=True)

if run_clicked:
    if not providers_selection:
        st.error("Select at least one provider.")
    else:
        slugs = providers_selection
        resolved_output = output_path.strip() or _get_download_path()
        with st.spinner("Running fetch... This may take several minutes."):
            out = io.StringIO()
            try:
                with redirect_stdout(out):
                    fetch_all_locations(
                        slugs=slugs,
                        output=resolved_output,
                        geocode=geocode,
                        use_zcta=use_zcta,
                        include_no_indicator=include_no_indicator,
                        days=days,
                    )
            except Exception as e:
                st.exception(e)
                st.stop()
        log = out.getvalue()
        st.success("Done!")
        st.code(log, language="text")
        # Offer download (useful when deployed on Streamlit Cloud)
        if os.path.isfile(resolved_output):
            with open(resolved_output, "rb") as f:
                st.download_button(
                    "Download CSV",
                    data=f.read(),
                    file_name=os.path.basename(resolved_output),
                    mime="text/csv",
                    type="primary",
                )
