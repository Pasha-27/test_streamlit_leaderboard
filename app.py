import streamlit as st
import pandas as pd
import gspread
import json
from google.oauth2.service_account import Credentials

# ---- Streamlit Config ----
st.set_page_config(
    page_title="Points Table Dashboard",
    page_icon="🏆",
    layout="wide",
)
st.title("🏆 Points Table")

SCOPE = [
    "https://www.googleapis.com/auth/spreadsheets.readonly",
    "https://www.googleapis.com/auth/drive.readonly",
]

@st.cache_resource
def get_gspread_client():
    svc = st.secrets["gcp_service_account"]
    if isinstance(svc, str):
        svc = json.loads(svc)
    creds = Credentials.from_service_account_info(svc, scopes=SCOPE)
    return gspread.authorize(creds)

@st.cache_data(ttl=300)
def load_points_data(sheet_name=None):
    client   = get_gspread_client()
    sheet_id = st.secrets["sheet_id"]
    sheet    = client.open_by_key(sheet_id)
    if sheet_name:
        ws = sheet.worksheet(sheet_name)
    else:
        ws = sheet.worksheets()[0]

    # Get all values (as strings)
    all_vals = ws.get_all_values()
    if not all_vals or len(all_vals) < 2:
        st.error("⚠️ No data rows found. Check your sheet ID & sharing permissions.")
        return pd.DataFrame(), ws.title
    header, *rows = all_vals
    df_raw = pd.DataFrame(rows, columns=header)
    return df_raw, ws.title

# ---- Sidebar worksheet picker ----
st.sidebar.header("📊 Worksheet Settings")
if st.sidebar.button("Show Available Worksheets"):
    try:
        client = get_gspread_client()
        sheet  = client.open_by_key(st.secrets["sheet_id"])
        for i, w in enumerate(sheet.worksheets(), start=1):
            st.sidebar.write(f"{i}. {w.title}")
    except Exception as e:
        st.sidebar.error(e)

# ---- Choose worksheet (optional) ----
worksheet_name = None  # or set from sidebar if you want!
df_raw, ws_name = load_points_data(worksheet_name)

# ---- Parse & aggregate data ----
def process_leaderboard(df_raw):
    # Find POD columns (by name)
    pod_cols = [c for c in df_raw.columns if "pod" in c.lower() or c.strip().isdigit()]
    if not pod_cols:
        pod_cols = df_raw.columns.tolist()
    # For each POD column, sum values down the column
    points = {}
    for pod in pod_cols:
        # Coerce to numeric, ignore blanks/invalid
        col_points = pd.to_numeric(df_raw[pod].str.replace(r"[^0-9.\-]", "", regex=True), errors="coerce")
        points[pod] = col_points.sum()
    # Build DataFrame
    summary = (
        pd.DataFrame(list(points.items()), columns=["POD Number", "Total Points"])
        .sort_values("Total Points", ascending=False)
        .reset_index(drop=True)
    )
    summary["Rank"] = summary.index + 1
    summary = summary[["Rank", "POD Number", "Total Points"]]
    return summary

df = process_leaderboard(df_raw)

if st.button("🔄 Refresh Data"):
    load_points_data.clear()
    get_gspread_client.clear()
    st.experimental_rerun()

# ---- Show Table & Raw Data ----
if not df.empty:
    def highlight_top_dark(row):
        color1 = "#444466"
        color2 = "#444450"
        color3 = "#353535"
        if row["Rank"] == 1: return [f"background-color:{color1};color:#fff"]*3
        if row["Rank"] == 2: return [f"background-color:{color2};color:#fff"]*3
        if row["Rank"] == 3: return [f"background-color:{color3};color:#fff"]*3
        return [""]*3

    st.subheader("🏆 Points Table")
    styled = df.style.apply(highlight_top_dark, axis=1)
    st.dataframe(styled, use_container_width=True)

    with st.expander("📋 Raw Data"):
        st.dataframe(df_raw, use_container_width=True)
        csv = df.to_csv(index=False)
        st.download_button("📥 Download CSV", data=csv, file_name="points_table.csv")
else:
    st.warning("No data available. Check your Google Sheet connection.")
