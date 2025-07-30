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

# ── Constants ───────────────────────────────────────────────────────────────────
SCOPE = [
    "https://www.googleapis.com/auth/spreadsheets.readonly",
    "https://www.googleapis.com/auth/drive.readonly",
]

# ── Initialize gspread client once ──────────────────────────────────────────────
@st.cache_resource
def get_gspread_client():
    # Load service account info from secrets
    svc_info = st.secrets["gcp_service_account"]
    # If you stored the JSON as a string, parse it
    if isinstance(svc_info, str):
        svc_info = json.loads(svc_info)
    creds = Credentials.from_service_account_info(svc_info, scopes=SCOPE)
    return gspread.authorize(creds)

# ── Load & clean data ───────────────────────────────────────────────────────────
@st.cache_data(ttl=300)  # refresh every 5 min
def load_points_data(worksheet_option="first"):
    try:
        client   = get_gspread_client()
        sheet_id = st.secrets["sheet_id"]
        sheet    = client.open_by_key(sheet_id)

        # pick the worksheet
        if worksheet_option == "first":
            ws = sheet.worksheets()[0]
        elif worksheet_option == "by_name":
            ws = sheet.worksheet("Sheet1")  # ← change as needed
        elif worksheet_option == "by_index":
            ws = sheet.worksheets()[0]
        else:
            ws = sheet.sheet1

        # Try records API (uses first row as header)
        records = ws.get_all_records()
        if records:
            df_raw = pd.DataFrame(records)
        else:
            # Fallback: get all values and re-construct
            all_vals = ws.get_all_values()
            if not all_vals or len(all_vals) < 2:
                st.error("⚠️ No data rows found. Check your sheet ID & sharing permissions.")
                return pd.DataFrame(), ws.title
            header, *rows = all_vals
            df_raw = pd.DataFrame(rows, columns=header)

        # Identify POD & Points columns
        pod_col = next(
            (c for c in df_raw.columns if any(k in c.lower() for k in ["pod","team","player","name"])),
            df_raw.columns[0]
        )
        pts_col = next(
            (c for c in df_raw.columns if any(k in c.lower() for k in ["point","score","total"])),
            (df_raw.columns[1] if len(df_raw.columns) > 1 else None)
        )

        if pts_col is None:
            st.error("⚠️ Couldn't locate any numeric column for points.")
            return pd.DataFrame(), ws.title

        # Build clean table
        clean = pd.DataFrame({
            "POD Number": df_raw[pod_col],
            "Total Points": pd.to_numeric(df_raw[pts_col], errors="coerce")
        }).dropna(subset=["Total Points"])
        if clean.empty:
