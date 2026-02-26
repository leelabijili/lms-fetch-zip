# Deploy to Streamlit Community Cloud

This guide walks you through deploying the **Service Interruptions by Location** UI to [Streamlit Community Cloud](https://share.streamlit.io) so you can share it via a URL.

## Prerequisites

- A [GitHub](https://github.com) account
- A [Streamlit Cloud](https://share.streamlit.io) account (free, sign in with GitHub)
- Your Downdetector API bearer token

## Step 1: Push Your Project to GitHub

1. Create a new repository on GitHub (e.g. `lms-fetch-zip`).
2. From your project folder, run:

   ```bash
   git init
   git add .
   git commit -m "Initial commit"
   git branch -M main
   git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO.git
   git push -u origin main
   ```

3. Make sure `.env` is in `.gitignore` (it already is) so your token is **not** committed.

## Step 2: Deploy on Streamlit Cloud

1. Go to [share.streamlit.io](https://share.streamlit.io) and sign in with GitHub.
2. Click **New app**.
3. Choose your repository, branch (e.g. `main`), and set:
   - **Main file path:** `fetch_locations_ui.py`
4. Expand **Advanced settings**.
5. Add your secret in **Secrets**:

   ```toml
   DOWNDETECTOR_BEARER_TOKEN = "your-bearer-token-here"
   ```

6. Click **Deploy**.

## Step 3: Wait for Deployment

The first run may take several minutes (geopandas, Census ZCTA download, etc.). You can monitor logs in the Streamlit Cloud dashboard.

## After Deployment

- Your app will be available at `https://YOUR_APP_NAME.streamlit.app`.
- Use the **Download CSV** button to save the output file when running on Cloud.
- Anyone with the URL can use the app and your Downdetector token. Share only with trusted users, or consider hosting privately.

## Troubleshooting

| Issue | Fix |
|-------|-----|
| "DOWNDETECTOR_BEARER_TOKEN not set" | Add the token in Streamlit Cloud **Secrets**. |
| App crashes on startup | Check the Cloud logs for Python/import errors. |
| Slow first run | Normal. Census ZCTA (~150MB) and ZIP CSV (~5MB) are downloaded once and cached. |
