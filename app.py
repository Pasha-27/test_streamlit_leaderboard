import streamlit as st
import pandas as pd
import gspread
import json
import re
from html import escape
from google.oauth2.service_account import Credentials
from gspread.exceptions import WorksheetNotFound

# ── Streamlit configuration ──────────────────────────────────────────────────
st.set_page_config(
    page_title="Points Table Dashboard",
    page_icon="🏆",
    layout="wide",
)
# (Heading intentionally removed)

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
        .fillna(0)
    )
    pod_numbers = [''.join(filter(str.isdigit, c)) or c for c in pod_cols]
    summary = pd.DataFrame({
        "POD Number": pod_numbers,
        "Total Points": totals.values
    })
    summary = summary.sort_values("Total Points", ascending=False).reset_index(drop=True)
    summary["Rank"] = summary.index + 1
    return summary[["Rank", "POD Number", "Total Points"]]

# ── Modern podium renderer for Top 3 ───────────────────────────────────────────
def render_podium(df_leader: pd.DataFrame):
    top3 = df_leader.head(3).copy()
    if top3.empty:
        return

    by_rank = {int(r): (str(n), float(p)) for r, n, p in zip(top3["Rank"], top3["POD Number"], top3["Total Points"])}

    def fmt_points(x: float) -> str:
        return f"{int(x):,}" if float(x).is_integer() else f"{x:,.2f}"

    r1_name, r1_pts = by_rank.get(1, ("—", 0))
    r2_name, r2_pts = by_rank.get(2, ("—", 0))
    r3_name, r3_pts = by_rank.get(3, ("—", 0))
    r1_name, r2_name, r3_name = escape(r1_name), escape(r2_name), escape(r3_name)

    podium_html = f"""
    <style>
      .podium-wrap {{
        display: grid;
        grid-template-columns: 1fr 1fr 1fr;
        gap: 24px;
        margin: 24px 0 8px 0;
        overflow: visible; /* allow floating badges */
      }}
      .podium-item {{
        position: relative;
        padding-top: 40px; /* room for floating badge */
      }}
      .podium-badge-top {{
        position: absolute;
        top: 0;
        left: 50%;
        transform: translate(-50%, -60%); /* float above and center */
        z-index: 5;
        background: linear-gradient(145deg, #111, #222);
        color: #fff;
        border: 2px solid rgba(255,255,255,0.18);
        border-radius: 999px;
        padding: 10px 16px;
        font-size: 28px;
        font-weight: 900;
        letter-spacing: 0.5px;
        box-shadow: 0 10px 24px rgba(0,0,0,0.45), 0 2px 0 rgba(255,255,255,0.06) inset;
        text-shadow: 0 2px 6px rgba(0,0,0,0.6);
        white-space: nowrap;
      }}
      .podium-card {{
        position: relative;
        border-radius: 18px;
        padding: 16px;
        color: #ffffff;
        background: linear-gradient(145deg, #2a2a2a, #131313);
        box-shadow: 0 10px 30px rgba(0,0,0,0.35), inset 0 1px 0 rgba(255,255,255,0.04);
        display: flex;
        align-items: center;           /* center vertically */
        justify-content: center;       /* center horizontally */
        min-height: 180px;
        overflow: visible;             /* don't clip floating bits */
      }}
      /* Contrast overlay for readability */
      .podium-card::after {{
        content: "";
        position: absolute;
        inset: 0;
        background: radial-gradient(ellipse at center, rgba(0,0,0,0.20), rgba(0,0,0,0.35));
        pointer-events: none;
        border-radius: 18px;
      }}
      .podium-1 {{ min-height: 240px; background: linear-gradient(150deg, #f2c94c, #b48a00); }}
      .podium-2 {{ min-height: 200px; background: linear-gradient(150deg, #bdc3c7, #808b96); }}
      .podium-3 {{ min-height: 180px; background: linear-gradient(150deg, #d29d63, #8e5a2a); }}

      .podium-content {{
        position: relative;
        z-index: 1;
        text-align: center;
        line-height: 1.15;
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 6px;
        text-shadow: 0 2px 8px rgba(0,0,0,0.55), 0 0 2px rgba(0,0,0,0.6);
      }}
      .podium-name {{
        font-size: 36px;               /* bigger name */
        font-weight: 900;
        letter-spacing: 0.2px;
        color: #ffffff;                 /* high contrast */
        margin: 0;
      }}
      .podium-points {{
        font-size: 36px;               /* doubled from 18px */
        font-weight: 800;
        color: #f7f7fb;                /* slightly brighter for contrast */
        opacity: 0.98;
        margin: 0;
      }}
      @media (max-width: 900px) {{
        .podium-name {{ font-size: 28px; }}
        .podium-points {{ font-size: 28px; }}
        .podium-badge-top {{ font-size: 24px; }}
      }}
    </style>

    <div class="podium-wrap">
      <div class="podium-item">
        <div class="podium-badge-top">#2</div>
        <div class="podium-card podium-2">
          <div class="podium-content">
            <div class="podium-name">POD {r2_name}</div>
            <div class="podium-points">Total: {fmt_points(r2_pts)}</div>
          </div>
        </div>
      </div>
      <div class="podium-item">
        <div class="podium-badge-top">#1 🏆</div>
        <div class="podium-card podium-1">
          <div class="podium-content">
            <div class="podium-name">POD {r1_name}</div>
            <div class="podium-points">Total: {fmt_points(r1_pts)}</div>
          </div>
        </div>
      </div>
      <div class="podium-item">
        <div class="podium-badge-top">#3</div>
        <div class="podium-card podium-3">
          <div class="podium-content">
            <div class="podium-name">POD {r3_name}</div>
            <div class="podium-points">Total: {fmt_points(r3_pts)}</div>
          </div>
        </div>
      </div>
    </div>
    """
    st.markdown(podium_html, unsafe_allow_html=True)

# ── Helper: hide index across Pandas versions (kept, though table is hidden) ──
def hide_index_compat(styler: pd.io.formats.style.Styler):
    if hasattr(styler, "hide"):
        try:
            return styler.hide(axis="index")
        except TypeError:
            pass
    if hasattr(styler, "hide_index"):
        return styler.hide_index()
    return styler

# ── (Optional) table for ranks 4+ — NOT rendered per request ──────────────────
def render_rest_table(_df_leader: pd.DataFrame):
    return  # hidden for now

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
