import streamlit as st
import pandas as pd
import gspread
import json
from google.oauth2.service_account import Credentials

# ── Streamlit page config ──────────────────────────────────────────────────────
st.set_page_config(
    page_title="Points Table Dashboard",
    page_icon="🏆",
    layout="wide",
)
st.title("🏆 Points Table")

# ── Google Sheets scope ─────────────────────────────────────────────────────────
SCOPE = [
    "https://www.googleapis.com/auth/spreadsheets.readonly",
    "https://www.googleapis.com/auth/drive.readonly",
]

# ── Cache the gspread client ───────────────────────────────────────────────────
@st.cache_resource
def get_gspread_client():
    svc = st.secrets["gcp_service_account"]
    if isinstance(svc, str):
        svc = json.loads(svc)
    creds = Credentials.from_service_account_info(svc, scopes=SCOPE)
    return gspread.authorize(creds)

# ── Load the full sheet into a DataFrame ────────────────────────────────────────
@st.cache_data(ttl=300)
def load_sheet(worksheet_name=None):
    client   = get_gspread_client()
    sheet_id = st.secrets["sheet_id"]
    sheet    = client.open_by_key(sheet_id)

    if worksheet_name:
        ws = sheet.worksheet(worksheet_name)
    else:
        ws = sheet.worksheets()[0]

    all_vals = ws.get_all_values()
    if not all_vals or len(all_vals) < 2:
        st.error("⚠️ No data rows found. Check your sheet ID & sharing permissions.")
        return pd.DataFrame(), ws.title

    header, *rows = all_vals
    df_raw = pd.DataFrame(rows, columns=header)
    return df_raw, ws.title

# ── Sidebar: show worksheets for debugging ───────────────────────────────────────
st.sidebar.header("📊 Worksheet Settings")
if st.sidebar.button("Show Available Worksheets"):
    try:
        sheet = get_gspread_client().open_by_key(st.secrets["sheet_id"])
        for i, w in enumerate(sheet.worksheets(), start=1):
            st.sidebar.write(f"{i}. {w.title}")
    except Exception as e:
        st.sidebar.error(e)

# ── Main load & refresh ─────────────────────────────────────────────────────────
df_raw, ws_name = load_sheet()
st.info(f"📋 Using data from worksheet: **{ws_name}**")

if st.button("🔄 Refresh Data"):
    load_sheet.clear()
    get_gspread_client.clear()
    st.experimental_rerun()

# ── Extract “Total points” row (sheet row 12 → df_raw.iloc[10]) ────────────────
df = pd.DataFrame()
try:
    # zero‑based: header was row1, df_raw[0] is row2 → so row12 is df_raw.iloc[10]
    total_row = df_raw.iloc[10]
    # pick your POD‑columns
    pod_cols = [c for c in df_raw.columns if "pod" in c.lower()]

    if not pod_cols:
        st.error("⚠️ Couldn’t find any POD columns in your sheet.")
    else:
        # clean & convert to numeric
        totals = (
            total_row[pod_cols]
            .astype(str)
            .str.replace(r"[^0-9.\-]", "", regex=True)
            .pipe(pd.to_numeric, errors="coerce")
        )
        # build summary table
        pod_nums = [
            int("".join(filter(str.isdigit, c))) for c in pod_cols
        ]
        summary = pd.DataFrame({
            "POD Number": pod_nums,
            "Total Points": totals.values
        })
        summary = summary.sort_values("Total Points", ascending=False).reset_index(drop=True)
        summary["Rank"] = summary.index + 1
        df = summary[["Rank", "POD Number", "Total Points"]]

except IndexError:
    st.error("⚠️ Your sheet doesn’t have a row 12. Adjust the row index in code.")
except Exception as e:
    st.error(f"Error processing totals row: {e}")

# ── Display the leaderboard ─────────────────────────────────────────────────────
if not df.empty:
    def highlight_top_dark(r):
        # Dark‑theme friendly highlights
        c1, c2, c3 = "#664400", "#555555", "#553300"
        if r["Rank"] == 1: return [f"background-color:{c1};color:#fff"]*3
        if r["Rank"] == 2: return [f"background-color:{c2};color:#fff"]*3
        if r["Rank"] == 3: return [f"background-color:{c3};color:#fff"]*3
        return [""]*3

    st.subheader("🏆 Points Table")
    styled = df.style.apply(highlight_top_dark, axis=1)
    st.dataframe(styled, use_container_width=True)

    with st.expander("📋 Raw Data"):
        st.dataframe(df_raw, use_container_width=True)
        csv = df.to_csv(index=False)
        st.download_button(
            "📥 Download CSV",
            data=csv,
            file_name="points_table.csv",
            mime="text/csv"
        )
else:
    st.warning("No data available. Check your Google Sheet connection.")
