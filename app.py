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
        margin: 12px 0 8px 0;
      }}
      .podium-card {{
        position: relative;
        border-radius: 18px;
        padding: 16px;
        color: #fff;
        background: linear-gradient(145deg, #2a2a2a, #131313);
        box-shadow: 0 10px 30px rgba(0,0,0,0.35), inset 0 1px 0 rgba(255,255,255,0.04);
        display: flex;
        align-items: flex-end;
        justify-content: center;
        min-height: 180px;
      }}
      .podium-1 {{
        min-height: 240px;
        background: linear-gradient(150deg, #f2c94c, #b48a00);
      }}
      .podium-2 {{
        min-height: 200px;
        background: linear-gradient(150deg, #bdc3c7, #808b96);
      }}
      .podium-3 {{
        min-height: 180px;
        background: linear-gradient(150deg, #d29d63, #8e5a2a);
      }}
      .podium-rank-badge {{
        position: absolute;
        top: -12px;
        left: -12px;
        background: rgba(0,0,0,0.55);
        border: 2px solid rgba(255,255,255,0.2);
        backdrop-filter: blur(4px);
        color: #fff;
        font-weight: 800;
        font-size: 20px;
        padding: 10px 14px;
        border-radius: 12px;
      }}
      .podium-content {{ text-align: center; line-height: 1.2; }}
      .podium-name {{ font-size: 28px; font-weight: 800; letter-spacing: 0.3px; margin-bottom: 6px; }}
      .podium-points {{ font-size: 18px; font-weight: 700; opacity: 0.95; }}
      @media (max-width: 900px) {{
        .podium-name {{ font-size: 22px; }}
        .podium-points {{ font-size: 16px; }}
      }}
    </style>

    <div class="podium-wrap">
      <div class="podium-card podium-2">
        <div class="podium-rank-badge">#2</div>
        <div class="podium-content">
          <div class="podium-name">POD {r2_name}</div>
          <div class="podium-points">Total: {fmt_points(r2_pts)}</div>
        </div>
      </div>
      <div class="podium-card podium-1">
        <div class="podium-rank-badge">#1 🏆</div>
        <div class="podium-content">
          <div class="podium-name">POD {r1_name}</div>
          <div class="podium-points">Total: {fmt_points(r1_pts)}</div>
        </div>
      </div>
      <div class="podium-card podium-3">
        <div class="podium-rank-badge">#3</div>
        <div class="podium-content">
          <div class="podium-name">POD {r3_name}</div>
          <div class="podium-points">Total: {fmt_points(r3_pts)}</div>
        </div>
      </div>
    </div>
    """
    st.markdown(podium_html, unsafe_allow_html=True)

# ── Helper: hide index across Pandas versions ─────────────────────────────────
def hide_index_compat(styler: pd.io.formats.style.Styler):
    """
    Works on Pandas 1.x and 2.x:
    - Pandas 2.x: use styler.hide(axis="index")
    - Pandas 1.x: fall back to styler.hide_index()
    - If neither exists, no-op.
    """
    if hasattr(styler, "hide"):
        try:
            return styler.hide(axis="index")
        except TypeError:
            pass
    if hasattr(styler, "hide_index"):
        return styler.hide_index()
    return styler  # graceful no-op

# ── Bigger, clean table for ranks 4+ (HTML + Styler) ───────────────────────────
def render_rest_table(df_leader: pd.DataFrame):
    if len(df_leader) <= 3:
        return
    df_rest = df_leader.iloc[3:].copy()

    def fmt(v):
        try:
            v = float(v)
            return f"{int(v):,}" if v.is_integer() else f"{v:,.2f}"
        except Exception:
            return v

    df_rest["Total Points"] = df_rest["Total Points"].apply(fmt)

    styled = (
        df_rest.style
        .set_table_styles([
            {"selector": "th", "props": [("font-size", "20px"), ("text-align", "left"),
                                         ("padding", "10px 12px"), ("background-color", "#1f1f1f"),
                                         ("color", "#eaeaea")]},
            {"selector": "td", "props": [("font-size", "18px"), ("padding", "10px 12px"),
                                         ("border-bottom", "1px solid #2a2a2a"),
                                         ("color", "#eeeeee")]}
        ])
    )
    styled = hide_index_compat(styled)
    st.markdown("### 📋 Ranks 4+")
    st.markdown(styled.to_html(), unsafe_allow_html=True)

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
        st.rerun()
    except Exception:
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
                df_channels = df_raw.iloc[1:8].copy()
                for _, row in df_channels.iterrows():
                    ch = row[channel_col]
                    prog_raw = str(row[progress_col]).strip()
                    prog_val = re.sub(r"[^0-9.]", "", prog_raw)
                    try:
                        prog = float(prog_val)
                    except Exception:
                        prog = 0.0
                    display_prog = min(max(prog, 0), 100)
                    if display_prog < 20:
                        bar_color = "#555555"
                    elif display_prog < 30:
                        bar_color = "#c0392b"
                    elif display_prog < 40:
                        bar_color = "#d35400"
                    elif display_prog < 50:
                        bar_color = "#f39c12"
                    else:
                        bar_color = "#27ae60"
                    st.markdown(
                        f"<div style='display:flex; justify-content:space-between; font-size:28px; font-weight:bold; margin-top:16px;'>"
                        f"<span>{escape(str(ch))}</span><span>{int(prog)}%</span></div>",
                        unsafe_allow_html=True
                    )
                    st.markdown(
                        f"<div style='background-color:#222222; border-radius:12px; width:100%; height:24px; margin-bottom:12px;'>"
                        f"<div style='width:{display_prog}%; background-color:{bar_color}; height:100%; border-radius:12px;'></div>"
                        f"</div>",
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
            # ── Modern Leaderboard tab (Top 3 podium + table for the rest) ──
            st.subheader(f"🏆 {label}")
            render_podium(df_leader)
            render_rest_table(df_leader)

            with st.expander("📥 Download & Raw Data"):
                csv = df_leader.to_csv(index=False)
                st.download_button(
                    "📥 Download Leaderboard CSV",
                    data=csv,
                    file_name=f"{label}_leaderboard.csv"
                )
                st.dataframe(df_raw, use_container_width=True)
