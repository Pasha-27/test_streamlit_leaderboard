import streamlit as st
import pandas as pd
import gspread
import json
import re
from google.oauth2.service_account import Credentials
from gspread.exceptions import WorksheetNotFound

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

# ── Utility: make header names unique ───────────────────────────────────────────
def make_unique(headers):
    seen = {}
    unique = []
    for h in headers:
        if h not in seen:
            seen[h] = 0
            unique.append(h)
        else:
            seen[h] += 1
            unique.append(f"{h}_{seen[h]}")
    return unique

# ── Cache the gspread client ───────────────────────────────────────────────────
@st.cache_resource
def get_gspread_client():
    svc = st.secrets.get("gcp_service_account")
    if not svc:
        st.error("⚠️ 'gcp_service_account' not found in secrets.")
        st.stop()
    if isinstance(svc, str):
        svc = json.loads(svc)
    creds = Credentials.from_service_account_info(svc, scopes=SCOPE)
    return gspread.authorize(creds)

# ── Load worksheet into DataFrame with unique headers ──────────────────────────
@st.cache_data(ttl=300)
def load_sheet(sheet_id: str, worksheet_name: str = None):
    client = get_gspread_client()
    sheet = client.open_by_key(sheet_id)
    try:
        ws = sheet.worksheet(worksheet_name) if worksheet_name else sheet.worksheets()[0]
    except WorksheetNotFound:
        available = [w.title for w in sheet.worksheets()]
        st.error(f"⚠️ Worksheet '{worksheet_name}' not found. Available: {available}")
        return pd.DataFrame(), worksheet_name or ""
    data = ws.get_all_values()
    if not data or len(data) < 2:
        st.error("⚠️ No data rows found. Check your sheet ID & sharing permissions.")
        return pd.DataFrame(), ws.title
    raw_header, *rows = data
    header = make_unique(raw_header)
    df_raw = pd.DataFrame(rows, columns=header)
    return df_raw, ws.title

# ── Build leaderboard from a totals row ────────────────────────────────────────
def build_leaderboard(df_raw: pd.DataFrame, total_row_index: int = 12) -> pd.DataFrame:
    try:
        total_row = df_raw.iloc[total_row_index]
    except Exception:
        st.error(f"⚠️ Totals row index {total_row_index} out of range.")
        return pd.DataFrame()
    pod_cols = [c for c in df_raw.columns if re.search(r"pod", c, re.I)]
    if not pod_cols:
        st.error("⚠️ No POD columns found. Ensure headers contain 'POD'.")
        return pd.DataFrame()
    totals = (
        total_row[pod_cols]
        .astype(str)
        .str.replace(r"[^0-9.\-]", "", regex=True)
        .pipe(pd.to_numeric, errors="coerce")
    )
    pod_numbers = [''.join(filter(str.isdigit, c)) or c for c in pod_cols]
    summary = pd.DataFrame({
        "POD Number": pod_numbers,
        "Total Points": totals.values
    })
    summary = summary.sort_values("Total Points", ascending=False).reset_index(drop=True)
    summary["Rank"] = summary.index + 1
    return summary[["Rank", "POD Number", "Total Points"]]

# ── Highlight styling for dark theme ───────────────────────────────────────────
def highlight_top_dark(row):
    colors = {1: "#664400", 2: "#555555", 3: "#553300"}
    c = colors.get(row["Rank"])
    return [f"background-color:{c};color:#fff"] * len(row) if c else [""] * len(row)

# ── Discover sheet IDs in secrets ─────────────────────────────────────────────
sheet_ids = []
for key, val in st.secrets.items():
    m = re.match(r"sheet_id(?:_(\d+))?$", key)
    if m:
        idx = int(m.group(1)) if m.group(1) else 1
        sheet_ids.append((idx, val))
if not sheet_ids:
    st.error("⚠️ No sheet IDs found in secrets. Add 'sheet_id_1', 'sheet_id_2', ...")
    st.stop()
sheet_ids.sort(key=lambda x: x[0])

# ── Load data and build tabs ───────────────────────────────────────────────────
dsets = []  # (tab_label, df_raw, df_leader)
for idx, sid in sheet_ids:
    if idx == 1:
        df_live, title_live = load_sheet(sid, worksheet_name="LIVE LEADERBOARD")
        df_leader = build_leaderboard(df_live, total_row_index=12)
        dsets.append((title_live, df_live, df_leader))
    elif idx == 2:
        df_ch, title_ch = load_sheet(sid, worksheet_name="Channel-View")
        dsets.append((title_ch, df_ch, pd.DataFrame()))
        df_pod, title_pod = load_sheet(sid, worksheet_name="POD-View")
        dsets.append((title_pod, df_pod, pd.DataFrame()))

# ── Refresh button clears caches ────────────────────────────────────────────────
if st.button("🔄 Refresh Data"):
    load_sheet.clear()
    get_gspread_client.clear()
    try:
        st.experimental_rerun()
    except AttributeError:
        pass

# ── Render tabs ────────────────────────────────────────────────────────────────
tab_labels = [label for label, _, _ in dsets]
tabs = st.tabs(tab_labels)
for tab, (label, df_raw, df_leader) in zip(tabs, dsets):
    with tab:
        if label == "Channel-View":
            st.subheader("📈 Channel Progress")
            if not df_raw.empty:
                channel_col = df_raw.columns[0]
                progress_col = df_raw.columns[5] if len(df_raw.columns) > 5 else df_raw.columns[-1]
                for _, row in df_raw.iloc[2:9].iterrows():
                    ch = row[channel_col]
                    prog_raw = str(row[progress_col]).strip()
                    prog_val = re.sub(r"[^0-9.]", "", prog_raw)
                    try:
                        prog = float(prog_val)
                    except:
                        prog = 0.0
                    # Dark-theme friendly bar colors
                    if prog < 20:
                        bar_color = "#777777"       # grey
                    elif prog < 30:
                        bar_color = "#c0392b"       # dark red
                    elif prog < 40:
                        bar_color = "#d35400"       # dark orange
                    elif prog < 50:
                        bar_color = "#f39c12"       # medium yellow
                    else:
                        bar_color = "#27ae60"       # vibrant green
                    # Display channel name & percentage larger
                    st.markdown(
                        f'<div style="display:flex; justify-content:space-between; font-size:28px; font-weight:bold; margin-top:16px;">'
                        f'<span>{ch}</span><span>{int(prog)}%</span></div>',
                        unsafe_allow_html=True
                    )
                    # Custom progress bar (height:24px)
                    st.markdown(
                        f'<div style="background-color:#222222; border-radius:12px; width:100%; height:24px; margin-bottom:12px;">'
                        f'<div style="width:{prog}%; background-color:{bar_color}; height:100%; border-radius:12px;"></div>'
                        f'</div>',
                        unsafe_allow_html=True
                    )
                with st.expander("📋 Raw Data"):
                    st.dataframe(df_raw, use_container_width=True)
            else:
                st.warning("No data available for Channel-View.")
        elif df_leader.empty:
            st.subheader(f"📋 {label} (Raw Data)")
            st.dataframe(df_raw, use_container_width=True)
        else:
            st.subheader(f"🏆 {label}")
            styled = df_leader.style.apply(highlight_top_dark, axis=1)
            st.dataframe(styled, use_container_width=True)
            with st.expander("📋 Raw Data"):
                st.dataframe(df_raw, use_container_width=True)
                csv = df_leader.to_csv(index=False)
                st.download_button(
                    "📥 Download CSV", data=csv,
                    file_name=f"{label}_leaderboard.csv"
                )
