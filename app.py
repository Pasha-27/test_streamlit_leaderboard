import streamlit as st
import pandas as pd
import gspread
import json
from google.oauth2.service_account import Credentials

# ── Streamlit configuration ──────────────────────────────────────────────────
st.set_page_config(
    page_title="Points Table Dashboard",
    page_icon="🏆",
    layout="wide",
)
st.title("🏆 Points Table Dashboard")

# ── Google Sheets API scope ────────────────────────────────────────────────────
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

# ── Load an entire worksheet by sheet_id ────────────────────────────────────────
@st.cache_data(ttl=300)
def load_sheet(sheet_id: str, worksheet_name: str = None):
    client = get_gspread_client()
    sheet = client.open_by_key(sheet_id)
    ws = sheet.worksheet(worksheet_name) if worksheet_name else sheet.worksheets()[0]
    data = ws.get_all_values()
    if not data or len(data) < 2:
        st.error("⚠️ No data rows found. Check your sheet ID & sharing permissions.")
        return pd.DataFrame(), ws.title
    header, *rows = data
    df_raw = pd.DataFrame(rows, columns=header)
    return df_raw, ws.title

# ── Build leaderboard from a totals row ────────────────────────────────────────
def build_leaderboard(df_raw: pd.DataFrame, total_row_index: int = 13) -> pd.DataFrame:
    """
    Extracts totals from the specified zero-based row index and returns
    a DataFrame with columns: Rank, POD Number, Total Points.
    """
    try:
        total_row = df_raw.iloc[total_row_index]
    except IndexError:
        st.error(f"⚠️ Row {total_row_index+1} not found in sheet. Adjust the index.")
        return pd.DataFrame()

    # Identify POD columns
    pod_cols = [c for c in df_raw.columns if "pod" in c.lower()]
    if not pod_cols:
        st.error("⚠️ No POD columns found. Ensure headers contain 'POD'.")
        return pd.DataFrame()

    # Parse and sum
    totals = (
        total_row[pod_cols]
        .astype(str)
        .str.replace(r"[^0-9.\-]", "", regex=True)
        .pipe(pd.to_numeric, errors="coerce")
    )

    # Map headers to pod numbers
    def extract_pod_num(header: str) -> int:
        digits = ''.join(filter(str.isdigit, header))
        return int(digits) if digits else header

    pod_numbers = [extract_pod_num(h) for h in pod_cols]

    # Build summary
    summary = pd.DataFrame({
        "POD Number": pod_numbers,
        "Total Points": totals.values
    })
    summary = summary.sort_values("Total Points", ascending=False).reset_index(drop=True)
    summary["Rank"] = summary.index + 1
    return summary.loc[:, ["Rank", "POD Number", "Total Points"]]

# ── Highlight styling for dark theme ───────────────────────────────────────────
def highlight_top_dark(row):
    c1, c2, c3 = "#664400", "#555555", "#553300"
    if row["Rank"] == 1:
        return [f"background-color:{c1};color:#fff"] * 3
    if row["Rank"] == 2:
        return [f"background-color:{c2};color:#fff"] * 3
    if row["Rank"] == 3:
        return [f"background-color:{c3};color:#fff"] * 3
    return [""] * 3

# ── Retrieve both sheet IDs from secrets ───────────────────────────────────────
sheet1_id = st.secrets["sheet_id_1"]
sheet2_id = st.secrets["sheet_id_2"]

# ── Load raw data for both sheets ──────────────────────────────────────────────
df1_raw, ws1_name = load_sheet(sheet1_id)
df2_raw, ws2_name = load_sheet(sheet2_id)

# ── Build leaderboards (row 14 → index 13) ────────────────────────────────────
df1 = build_leaderboard(df1_raw, total_row_index=13)
df2 = build_leaderboard(df2_raw, total_row_index=13)

# ── Refresh button clears cache ────────────────────────────────────────────────
if st.button("🔄 Refresh Data"):
    load_sheet.clear()
    get_gspread_client.clear()
    st.experimental_rerun()

# ── Display in tabs ─────────────────────────────────────────────────────────────
tab1, tab2 = st.tabs([ws1_name, ws2_name])

with tab1:
    st.subheader(f"🏆 {ws1_name} Leaderboard")
    if not df1.empty:
        styled1 = df1.style.apply(highlight_top_dark, axis=1)
        st.dataframe(styled1, use_container_width=True)
        with st.expander("📋 Raw Data"):
            st.dataframe(df1_raw, use_container_width=True)
            csv1 = df1.to_csv(index=False)
            st.download_button("📥 Download CSV", data=csv1, file_name=f"{ws1_name}_leaderboard.csv")
    else:
        st.warning("No leaderboard data for this sheet.")

with tab2:
    st.subheader(f"🏆 {ws2_name} Leaderboard")
    if not df2.empty:
        styled2 = df2.style.apply(highlight_top_dark, axis=1)
        st.dataframe(styled2, use_container_width=True)
        with st.expander("📋 Raw Data"):
            st.dataframe(df2_raw, use_container_width=True)
            csv2 = df2.to_csv(index=False)
            st.download_button("📥 Download CSV", data=csv2, file_name=f"{ws2_name}_leaderboard.csv")
    else:
        st.warning("No leaderboard data for this sheet.")
