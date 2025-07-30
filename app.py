import streamlit as st
import pandas as pd
import gspread
import json
from google.oauth2.service_account import Credentials

# ── Page configuration ─────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Points Table Dashboard",
    page_icon="🏆",
    layout="wide"
)
st.title("🏆 Points Table Dashboard")

# ── Google Sheets scope ─────────────────────────────────────────────────────────
SCOPE = [
    "https://www.googleapis.com/auth/spreadsheets.readonly",
    "https://www.googleapis.com/auth/drive.readonly",
]

# ── Cache the gspread client ───────────────────────────────────────────────────
@st.cache(allow_output_mutation=True)
def get_gspread_client():
    svc_info = st.secrets["gcp_service_account"]
    if isinstance(svc_info, str):
        svc_info = json.loads(svc_info)
    creds = Credentials.from_service_account_info(svc_info, scopes=SCOPE)
    return gspread.authorize(creds)

# ── Load & clean the data ──────────────────────────────────────────────────────
@st.cache_data(ttl=300)
def load_points_data(worksheet_option="first"):
    try:
        client   = get_gspread_client()
        sheet_id = st.secrets["sheet_id"]
        sheet    = client.open_by_key(sheet_id)

        # pick the worksheet
        if worksheet_option == "first":
            ws = sheet.worksheets()[0]
        elif worksheet_option == "by_name":
            ws = sheet.worksheet("Sheet1")  # ← rename if needed
        else:
            ws = sheet.sheet1

        records = ws.get_all_records()
        if records:
            df_raw = pd.DataFrame(records)
        else:
            all_vals = ws.get_all_values()
            if not all_vals or len(all_vals) < 2:
                st.error("⚠️ No data rows found. Check your sheet ID & sharing permissions.")
                return pd.DataFrame(), ws.title
            header, *rows = all_vals
            df_raw = pd.DataFrame(rows, columns=header)

        # auto-detect columns
        pod_col = next(
            (c for c in df_raw.columns if any(k in c.lower() for k in ["pod","team","player","name"])),
            df_raw.columns[0]
        )
        pts_col = next(
            (c for c in df_raw.columns if any(k in c.lower() for k in ["point","score","total"])),
            (df_raw.columns[1] if len(df_raw.columns) > 1 else None)
        )
        if pts_col is None:
            st.error("⚠️ Couldn't locate a numeric column for points.")
            return pd.DataFrame(), ws.title

        clean = pd.DataFrame({
            "POD Number": df_raw[pod_col],
            "Total Points": pd.to_numeric(df_raw[pts_col], errors="coerce")
        }).dropna(subset=["Total Points"])
        if clean.empty:
            st.warning("No numeric point data found after cleaning.")
            return pd.DataFrame(), ws.title

        clean = clean.sort_values("Total Points", ascending=False).reset_index(drop=True)
        clean["Rank"] = clean.index + 1
        clean = clean[["Rank", "POD Number", "Total Points"]]
        return clean, ws.title

    except Exception as e:
        st.error(f"Error loading data from Google Sheets: {e}")
        return pd.DataFrame(), "Error"

# ── Sidebar for debugging ────────────────────────────────────────────────────────
st.sidebar.header("📊 Worksheet Settings")
if st.sidebar.button("Show Available Worksheets"):
    try:
        client = get_gspread_client()
        sheet  = client.open_by_key(st.secrets["sheet_id"])
        for i, w in enumerate(sheet.worksheets(), start=1):
            st.sidebar.write(f"{i}. {w.title}")
    except Exception as e:
        st.sidebar.error(e)

# ── Main ────────────────────────────────────────────────────────────────────────
df, ws_name = load_points_data("first")
st.info(f"📋 Using data from worksheet: **{ws_name}**")

if st.button("🔄 Refresh Data"):
    load_points_data.clear()
    st.experimental_rerun()

if not df.empty:
    c1, c2, c3 = st.columns(3)
    c1.metric("Total PODs",     len(df))
    c2.metric("Total Points",   f"{df['Total Points'].sum():,.0f}")
    c3.metric("Average Points", f"{df['Total Points'].mean():.1f}")

    st.subheader("🏆 Points Table")
    def highlight_top_3(r):
        if r["Rank"] == 1: return ["background-color:#FFD700"]*3
        if r["Rank"] == 2: return ["background-color:#C0C0C0"]*3
        if r["Rank"] == 3: return ["background-color:#CD7F32"]*3
        return [""]*3

    styled = df.style.apply(highlight_top_3, axis=1)
    st.dataframe(styled, use_container_width=True)

    with st.expander("📋 Raw Data"):
        st.dataframe(df, use_container_width=True)
        csv = df.to_csv(index=False)
        st.download_button("📥 Download CSV", data=csv, file_name="points_table.csv")
else:
    st.warning("No data available. Check your Google Sheet connection.")
