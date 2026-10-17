# France Top 50 Playlist Analytics — Streamlit

## Run locally
1. Install Python 3.10 or newer.
2. Extract this ZIP and open a terminal in the `france_top50_streamlit` folder.
3. Install dependencies:
   `python -m pip install -r requirements.txt`
4. Start the app:
   `streamlit run app.py`

## Add your dataset
Upload your cleaned CSV in the sidebar. Alternatively, place it at `data/clean_france_top50.csv`.

Expected fields: `song`, `artist`, `is_explicit`, `date`, `position`, `popularity`, `duration_min`, `album_type`.
Common alternatives such as `track_name`, `rank`, and `duration_minutes` are recognized.

## Sections
- Overview
- Audience Sensitivity
- Content Compliance
- Format Preferences
- Data Explorer with CSV download

The explicit-content flag is treated as supplied metadata; this app does not certify legal or platform-policy compliance.
