# Share Your Streamlit App via URL

## Option A: Streamlit Community Cloud (requires GitHub)

1. Push your repo to GitHub (Streamlit Cloud does not support Bitbucket):
   ```bash
   git remote add github https://github.com/YOUR_USERNAME/lms-fetch-zip.git
   git push -u github main
   ```

2. Go to [share.streamlit.io](https://share.streamlit.io) → **New app**

3. Choose repo `YOUR_USERNAME/lms-fetch-zip`, branch `main`, file `fetch_locations_ui.py`

4. In **Advanced settings** → **Secrets**, add:
   ```toml
   DOWNDETECTOR_BEARER_TOKEN = "your-token-here"
   ```

5. Click **Deploy** and share the URL: `https://YOUR_APP_NAME.streamlit.app`

### Troubleshooting "No data" on Streamlit Cloud

If the app returns "No location records retrieved" on Cloud but works locally:

1. Expand **Debug (Cloud)** and check **Enable verbose debug output**.
2. Run fetch again. The log will show:
   - `Token present: yes/no`
   - `datetime.utcnow()` (server time used for date range)
   - Per-slug: request URL, `status`, `records_in_page`
3. Compare the Cloud log with a local run using `python fetch_locations.py --debug`.
4. Verify secrets: In Streamlit Cloud **Settings → Secrets**, the key must be `DOWNDETECTOR_BEARER_TOKEN` (top-level). Example:
   ```toml
   DOWNDETECTOR_BEARER_TOKEN = "your-token-here"
   ```
5. Try "Last 7 days" instead of 1 day to increase the chance of finding data.

## Option B: Render or Railway (works with Bitbucket)

Connect your Bitbucket repo and deploy. Set build/start commands and add `DOWNDETECTOR_BEARER_TOKEN` as an environment variable.
