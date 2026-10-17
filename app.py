from pathlib import Path
import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(page_title="France Top 50 Analytics", page_icon="🎵", layout="wide")
st.title("France Top 50 Playlist Analytics")
st.caption("Audience Sensitivity • Content Compliance • Format Preference")

ALIASES = {
    "song": ["song", "track_name", "track", "name", "title"],
    "artist": ["artist", "artist_name", "artists"],
    "is_explicit": ["is_explicit", "explicit", "explicit_content"],
    "date": ["date", "snapshot_date", "playlist_date", "chart_date"],
    "position": ["position", "chart_position", "rank", "track_position"],
    "popularity": ["popularity", "popularity_score"],
    "duration_min": ["duration_min", "duration_minutes", "track_duration_min"],
    "album_type": ["album_type", "release_type", "album_format"],
}

def normalize_columns(frame):
    frame = frame.copy()
    lookup = {str(c).strip().lower(): c for c in frame.columns}
    renames = {}
    for target, candidates in ALIASES.items():
        for candidate in candidates:
            if candidate in lookup:
                original = lookup[candidate]
                if original != target:
                    renames[original] = target
                break
    return frame.rename(columns=renames)

def explicit_values(series):
    mapping = {"true": True, "false": False, "1": True, "0": False,
               "yes": True, "no": False, "y": True, "n": False}
    return series.astype(str).str.strip().str.lower().map(mapping)

@st.cache_data(show_spinner=False)
def prepare(frame):
    data = normalize_columns(frame)
    for col in ["song", "artist", "album_type"]:
        if col in data:
            data[col] = data[col].astype("string").str.strip()
    for col in ["position", "popularity", "duration_min"]:
        if col in data:
            data[col] = pd.to_numeric(data[col], errors="coerce")
    if "date" in data:
        data["date"] = pd.to_datetime(data["date"], errors="coerce")
    data["explicit_flag"] = (
        explicit_values(data["is_explicit"]) if "is_explicit" in data
        else pd.Series(pd.NA, index=data.index, dtype="boolean")
    )
    if "duration_min" in data:
        data["duration_group"] = pd.cut(
            data["duration_min"], [0, 2, 3, 4, 5, float("inf")],
            labels=["Under 2 min", "2–3 min", "3–4 min", "4–5 min", "5+ min"],
            right=False
        )
    if "position" in data:
        data["chart_position_group"] = pd.cut(
            data["position"], [0, 10, 25, 50],
            labels=["Top 10", "Positions 11–25", "Positions 26–50"],
            include_lowest=True
        )
    if "popularity" in data:
        data["popularity_group"] = pd.cut(
            data["popularity"], [-1, 25, 50, 75, 100],
            labels=["0–25", "26–50", "51–75", "76–100"],
            include_lowest=True
        )
    return data

st.sidebar.header("Data")
uploaded = st.sidebar.file_uploader("Upload cleaned France Top 50 CSV", type=["csv"])
local_candidates = [
    Path("data/clean_france_top50.csv"), Path("data/df_clean.csv"),
    Path("clean_france_top50.csv"), Path("df_clean.csv")
]
raw, source = None, None
if uploaded is not None:
    try:
        raw, source = pd.read_csv(uploaded), uploaded.name
    except Exception as exc:
        st.error(f"Could not read CSV: {exc}")
        st.stop()
else:
    for candidate in local_candidates:
        if candidate.exists():
            try:
                raw, source = pd.read_csv(candidate), str(candidate)
                break
            except Exception:
                continue

if raw is None:
    st.info("Upload your cleaned CSV in the sidebar to start exploring the project.")
    st.markdown(
        "**Expected fields:** `song`, `artist`, `is_explicit`, `date`, `position`, "
        "`popularity`, `duration_min`, `album_type`.\n\n"
        "Common alternatives such as `track_name`, `rank`, and `duration_minutes` "
        "are recognized automatically."
    )
    st.stop()

df = prepare(raw)
required = ["song", "artist", "is_explicit", "date", "position",
            "popularity", "duration_min", "album_type"]
missing = [col for col in required if col not in df.columns]
if missing:
    st.error("Required columns not found: " + ", ".join(missing))
    st.write("Columns detected:", list(df.columns))
    st.stop()

st.sidebar.caption(f"Source: {source}")
st.sidebar.caption(f"Records loaded: {len(df):,}")
st.sidebar.header("Filters")
artists = sorted(df["artist"].dropna().astype(str).unique())
albums = sorted(df["album_type"].dropna().astype(str).unique())
chosen_artists = st.sidebar.multiselect("Artist", artists)
chosen_albums = st.sidebar.multiselect("Album type", albums)
explicit_filter = st.sidebar.selectbox("Explicit flag", ["All", "Explicit", "Non-explicit", "Unknown"])
section = st.sidebar.radio(
    "Dashboard section",
    ["Overview", "Audience Sensitivity", "Content Compliance", "Format Preferences", "Data Explorer"]
)

data = df.copy()
if chosen_artists:
    data = data[data["artist"].astype(str).isin(chosen_artists)]
if chosen_albums:
    data = data[data["album_type"].astype(str).isin(chosen_albums)]
if explicit_filter == "Explicit":
    data = data[data["explicit_flag"] == True]
elif explicit_filter == "Non-explicit":
    data = data[data["explicit_flag"] == False]
elif explicit_filter == "Unknown":
    data = data[data["explicit_flag"].isna()]
if data.empty:
    st.warning("No rows match these filters. Please change or clear the filters.")
    st.stop()

valid_flags = data["explicit_flag"].dropna()
explicit_pct = valid_flags.eq(True).mean() * 100 if len(valid_flags) else None

def show_kpis(frame):
    a, b, c, d, e = st.columns(5)
    a.metric("Playlist records", f"{len(frame):,}")
    b.metric("Unique songs", f"{frame['song'].nunique():,}")
    c.metric("Unique artists", f"{frame['artist'].nunique():,}")
    d.metric("Avg. popularity", f"{frame['popularity'].mean():.1f}" if frame["popularity"].notna().any() else "N/A")
    e.metric("Explicit tracks", f"{explicit_pct:.1f}%" if explicit_pct is not None else "N/A")

if section == "Overview":
    st.subheader("Overview Dashboard")
    show_kpis(data)
    left, right = st.columns(2)
    with left:
        counts = data["album_type"].fillna("Unknown").value_counts().rename_axis("Album type").reset_index(name="Tracks")
        st.plotly_chart(px.bar(counts, x="Album type", y="Tracks", title="Tracks by Album Type"), use_container_width=True)
    with right:
        counts = data["duration_group"].astype("string").fillna("Unknown").value_counts(sort=False).rename_axis("Duration group").reset_index(name="Tracks")
        st.plotly_chart(px.bar(counts, x="Duration group", y="Tracks", title="Tracks by Duration Group"), use_container_width=True)
    trend_data = data.dropna(subset=["date", "explicit_flag"]).copy()
    if not trend_data.empty:
        trend_data["Content flag"] = trend_data["explicit_flag"].map({True: "Explicit", False: "Non-explicit"})
        trend = trend_data.groupby([pd.Grouper(key="date", freq="D"), "Content flag"]).size().reset_index(name="Tracks")
        st.plotly_chart(px.line(trend, x="date", y="Tracks", color="Content flag", markers=True, title="Daily Records by Content Flag"), use_container_width=True)

elif section == "Audience Sensitivity":
    st.subheader("Audience Sensitivity")
    show_kpis(data)
    counts = data["explicit_flag"].map({True: "Explicit", False: "Non-explicit"}).fillna("Unknown").value_counts().rename_axis("Content flag").reset_index(name="Tracks")
    left, right = st.columns(2)
    with left:
        st.plotly_chart(px.pie(counts, names="Content flag", values="Tracks", title="Explicit vs Non-explicit"), use_container_width=True)
    with right:
        artist_counts = data.groupby("artist", dropna=True).agg(Track_records=("song", "count")).reset_index().nlargest(15, "Track_records")
        st.plotly_chart(px.bar(artist_counts, x="artist", y="Track_records", title="Artists with Most Records"), use_container_width=True)
    trend_data = data.dropna(subset=["date", "explicit_flag"]).copy()
    if not trend_data.empty:
        trend_data["Content flag"] = trend_data["explicit_flag"].map({True: "Explicit", False: "Non-explicit"})
        trend = trend_data.groupby([pd.Grouper(key="date", freq="D"), "Content flag"]).size().reset_index(name="Tracks")
        st.plotly_chart(px.line(trend, x="date", y="Tracks", color="Content flag", markers=True, title="Content Records Over Time"), use_container_width=True)
    st.caption("The explicit flag is a metadata indicator, not a complete measure of audience sensitivity.")

elif section == "Content Compliance":
    st.subheader("Content Compliance Review")
    show_kpis(data)
    data = data.copy()
    data["Content flag"] = data["explicit_flag"].map({True: "Explicit", False: "Non-explicit"}).fillna("Unknown")
    left, right = st.columns(2)
    with left:
        album = data.groupby(["album_type", "Content flag"], dropna=False).size().reset_index(name="Tracks")
        st.plotly_chart(px.bar(album, x="album_type", y="Tracks", color="Content flag", barmode="group", title="Content Flags by Album Type"), use_container_width=True)
    with right:
        chart = data.groupby(["chart_position_group", "Content flag"], observed=False).size().reset_index(name="Tracks")
        st.plotly_chart(px.bar(chart, x="chart_position_group", y="Tracks", color="Content flag", barmode="group", title="Content Flags by Chart Position"), use_container_width=True)
    popularity = data.groupby(["popularity_group", "Content flag"], observed=False).size().reset_index(name="Tracks")
    st.plotly_chart(px.bar(popularity, x="popularity_group", y="Tracks", color="Content flag", barmode="group", title="Content Flags by Popularity"), use_container_width=True)
    summary = data.groupby("Content flag", dropna=False).agg(
        Track_count=("song", "count"), Avg_popularity=("popularity", "mean"),
        Avg_chart_position=("position", "mean"), Avg_duration_min=("duration_min", "mean")
    ).reset_index().round(2)
    st.dataframe(summary, use_container_width=True, hide_index=True)
    st.warning("This section analyzes the dataset's explicit flag only. It does not certify legal or platform-policy compliance.")

elif section == "Format Preferences":
    st.subheader("Format Preference Analysis")
    show_kpis(data)
    left, right = st.columns(2)
    with left:
        duration = data.groupby("duration_group", observed=False).size().reset_index(name="Tracks")
        st.plotly_chart(px.bar(duration, x="duration_group", y="Tracks", title="Tracks by Duration Group"), use_container_width=True)
    with right:
        album = data.groupby("album_type", dropna=False).agg(
            Tracks=("song", "count"), Average_duration=("duration_min", "mean"),
            Average_popularity=("popularity", "mean"), Average_position=("position", "mean")
        ).reset_index().round(2)
        st.plotly_chart(px.bar(album, x="album_type", y="Tracks", title="Tracks by Album Type"), use_container_width=True)
    chart_duration = data.groupby("chart_position_group", observed=False)["duration_min"].mean().reset_index(name="Average duration (minutes)")
    st.plotly_chart(px.bar(chart_duration, x="chart_position_group", y="Average duration (minutes)", title="Average Duration by Chart Position"), use_container_width=True)
    pop_duration = data.groupby("popularity_group", observed=False)["duration_min"].mean().reset_index(name="Average duration (minutes)")
    st.plotly_chart(px.bar(pop_duration, x="popularity_group", y="Average duration (minutes)", title="Average Duration by Popularity"), use_container_width=True)
    st.subheader("Album-type summary")
    st.dataframe(album, use_container_width=True, hide_index=True)

else:
    st.subheader("Data Explorer")
    search = st.text_input("Search song or artist")
    shown = data.copy()
    if search.strip():
        mask = shown["song"].fillna("").astype(str).str.contains(search, case=False, na=False) | shown["artist"].fillna("").astype(str).str.contains(search, case=False, na=False)
        shown = shown[mask]
    columns = [c for c in ["date", "position", "song", "artist", "is_explicit", "duration_min", "album_type", "popularity"] if c in shown.columns]
    st.dataframe(shown[columns], use_container_width=True, hide_index=True)
    st.download_button("Download filtered CSV", shown.to_csv(index=False).encode("utf-8"), "france_top50_filtered.csv", "text/csv")

st.divider()
st.caption("Results are descriptive and depend on the loaded dataset. Associations do not establish causation.")
