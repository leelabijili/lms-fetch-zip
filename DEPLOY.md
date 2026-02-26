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

## Option B: Render or Railway (works with Bitbucket)

Connect your Bitbucket repo and deploy. Set build/start commands and add `DOWNDETECTOR_BEARER_TOKEN` as an environment variable.
