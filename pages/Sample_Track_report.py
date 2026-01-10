import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
import plotly.graph_objects as go
import plotly.express as px
import requests
from io import BytesIO

# PDF generation (ReportLab)
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
)
from reportlab.lib.styles import getSampleStyleSheet

# =========================
# Page Config
# =========================
st.set_page_config(
    page_title="Sample Track Analytics Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# =========================
# Custom CSS (English only)
# =========================
st.markdown("""
<style>
    .main-header {
        font-size: 2.3rem;
        font-weight: 800;
        color: #1E3A8A;
        margin-bottom: 1rem;
        text-align: center;
        padding: 1rem;
        background: linear-gradient(90deg, #EFF6FF, #DBEAFE);
        border-radius: 12px;
        border-left: 6px solid #3B82F6;
    }
    .section-header {
        font-size: 1.6rem;
        font-weight: 700;
        color: #1E40AF;
        margin-top: 1.2rem;
        margin-bottom: 0.8rem;
        padding-bottom: 0.4rem;
        border-bottom: 3px solid #60A5FA;
    }
    .metric-card {
        background: linear-gradient(135deg, #F0F9FF, #E0F2FE);
        padding: 1.2rem;
        border-radius: 14px;
        border-left: 5px solid #0EA5E9;
        box-shadow: 0 4px 8px rgba(0, 0, 0, 0.06);
    }
    .kpi-label {
        font-size: 0.85rem;
        font-weight: 600;
        color: #475569;
        letter-spacing: 0.4px;
        text-transform: uppercase;
    }
    .kpi-value {
        font-size: 2.0rem;
        font-weight: 800;
        color: #1E3A8A;
        margin: 0.4rem 0;
    }
    .kpi-change {
        font-size: 0.85rem;
        font-weight: 600;
        color: #334155;
    }
    .hint {
        color: #64748B;
        font-size: 0.9rem;
    }
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-header">📊 Sample Track Analytics Dashboard</div>', unsafe_allow_html=True)

# =========================
# Google Sheet Config (from your URL)
# =========================
# Your link:
# https://docs.google.com/spreadsheets/d/1lkztBZ4eG1BQx-52XgnA6w8YIiw-Sm85pTlQQziurfw/edit?gid=1114674433#gid=1114674433
SPREADSHEET_KEY = "1lkztBZ4eG1BQx-52XgnA6w8YIiw-Sm85pTlQQziurfw"
WORKSHEET_NAME = "Test"  # Must match the sheet tab name

# =========================
# GeoJSON sources (Afghanistan)
# =========================
# If your hosting blocks GitHub downloads, the map will not load.
# The code includes a clear error message + fallback behavior.
ADM1_GEOJSON_URL = "https://raw.githubusercontent.com/wmgeolab/geoBoundaries/main/releaseData/gbOpen/AFG/ADM1/geoBoundaries-AFG-ADM1.geojson"
ADM2_GEOJSON_URL = "https://raw.githubusercontent.com/wmgeolab/geoBoundaries/main/releaseData/gbOpen/AFG/ADM2/geoBoundaries-AFG-ADM2_simplified.geojson"

# =========================
# Helpers
# =========================
def norm_text(x: str) -> str:
    """Normalize names for matching (Province/District)."""
    s = str(x).strip().lower()
    s = s.replace("_", " ").replace("’", "'").replace("`", "'")
    s = s.replace("  ", " ")
    s = s.replace("sar e pul", "sar-e-pul")
    s = s.replace("sare pul", "sar-e-pul")
    s = s.replace("maidan wardak", "maidān wardak").replace("maydan wardak", "maidān wardak")
    # Keep hyphens but normalize spaces around them
    s = s.replace(" - ", "-").replace("- ", "-").replace(" -", "-")
    return s

def remove_total_rows(df: pd.DataFrame) -> pd.DataFrame:
    """Remove rows containing 'total' in Region/Province/District (case-insensitive)."""
    df = df.copy()
    for c in ["Region", "Province", "District"]:
        if c in df.columns:
            df[c] = df[c].astype(str).str.strip()
            df = df[~df[c].str.contains(r"\btotal\b", case=False, na=False)]
    return df

def safe_num(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce").fillna(0)

def find_prefixed_metric(df_cols, prefix, keywords):
    """
    Find a column that starts with prefix and contains any of the keywords.
    Example: prefix='CBE-' keywords=['target','sample'].
    """
    cols = [str(c).strip() for c in df_cols]
    candidates = [c for c in cols if c.startswith(prefix)]
    for kw in keywords:
        for c in candidates:
            if kw.lower() in c.lower():
                return c
    # fallback: if only one candidate exists
    if len(candidates) == 1:
        return candidates[0]
    return None

def detect_comment_columns(df: pd.DataFrame) -> list:
    """Detect comment columns automatically."""
    cols = []
    for c in df.columns:
        cl = str(c).strip().lower()
        if "comment" in cl or cl.endswith("-comments") or cl.endswith("_comments"):
            cols.append(c)
    return cols

def summarize_comments(df_raw: pd.DataFrame) -> dict:
    """
    Summarize comments: total non-empty comment cells and top frequent short texts (if any).
    """
    comment_cols = detect_comment_columns(df_raw)
    if not comment_cols:
        return {"comment_cols": [], "non_empty": 0, "top": []}

    tmp = df_raw[comment_cols].copy()
    # Convert everything to string, treat blanks as empty
    tmp = tmp.applymap(lambda x: "" if pd.isna(x) else str(x).strip())
    non_empty = int((tmp != "").sum().sum())

    # Collect short comments for frequency
    all_comments = []
    for c in comment_cols:
        vals = tmp[c].tolist()
        all_comments.extend([v for v in vals if v])

    # Basic frequency (limit)
    from collections import Counter
    top = Counter(all_comments).most_common(10)

    return {"comment_cols": comment_cols, "non_empty": non_empty, "top": top}

def build_tool_view(df_raw: pd.DataFrame, tool: str) -> pd.DataFrame:
    """
    A/B/C = Region/Province/District (by position).
    Columns with prefixes:
      CBE-... -> CBE metrics
      PBs-... -> PBs metrics
      Total-... -> Total metrics
    Tool choices:
      - CBE: uses CBE- columns
      - PBs: uses PBs- columns
      - Total: uses Total- columns; if Total- missing, sums CBE+PBs where possible.
    Returns standardized columns:
      Region, Province, District,
      Total_Sample_Size, Total_Received, Approved, Pending, Rejected, Total_Checked, Progress_Percentage, Progress_Status
    """
    df = df_raw.copy()
    if df.shape[1] < 3:
        raise ValueError("The sheet must have at least 3 columns (A=Region, B=Province, C=District).")

    cols = list(df.columns)
    df = df.rename(columns={cols[0]: "Region", cols[1]: "Province", cols[2]: "District"})

    df["Region"] = df["Region"].astype(str).str.strip()
    df["Province"] = df["Province"].astype(str).str.strip()
    df["District"] = df["District"].astype(str).str.strip()

    df = remove_total_rows(df)

    prefix_map = {"CBE": "CBE-", "PBs": "PBs-", "Total": "Total-"}
    prefix = prefix_map[tool]

    # Resolve metric columns from sheet headers
    col_target = find_prefixed_metric(df.columns, prefix, ["target", "sample", "samplesize", "sample_size", "total_sample"])
    col_received = find_prefixed_metric(df.columns, prefix, ["received", "collected", "collection", "data_received"])
    col_approved = find_prefixed_metric(df.columns, prefix, ["approved", "approve"])
    col_pending = find_prefixed_metric(df.columns, prefix, ["pending", "review", "in_review", "under_review"])
    col_rejected = find_prefixed_metric(df.columns, prefix, ["rejected", "reject"])
    col_checked = find_prefixed_metric(df.columns, prefix, ["checked", "reviewed", "total_checked"])

    def get_col(colname):
        if colname and colname in df.columns:
            return safe_num(df[colname])
        return pd.Series([0] * len(df), index=df.index, dtype=float)

    out = df[["Region", "Province", "District"]].copy()
    out["Total_Sample_Size"] = get_col(col_target)
    out["Total_Received"] = get_col(col_received)
    out["Approved"] = get_col(col_approved)
    out["Pending"] = get_col(col_pending)
    out["Rejected"] = get_col(col_rejected)

    checked_explicit = get_col(col_checked)
    out["Total_Checked"] = np.where(
        checked_explicit > 0,
        checked_explicit,
        out["Approved"] + out["Pending"] + out["Rejected"]
    )

    # If Total tool has no Total- target, attempt sum of CBE + PBs
    if tool == "Total" and out["Total_Sample_Size"].sum() == 0:
        cbe = build_tool_view(df_raw, "CBE")
        pbs = build_tool_view(df_raw, "PBs")
        key = ["Region", "Province", "District"]
        m = cbe.merge(pbs, on=key, how="outer", suffixes=("_CBE", "_PBs")).fillna(0)
        out = m[key].copy()
        out["Total_Sample_Size"] = m["Total_Sample_Size_CBE"] + m["Total_Sample_Size_PBs"]
        out["Total_Received"] = m["Total_Received_CBE"] + m["Total_Received_PBs"]
        out["Approved"] = m["Approved_CBE"] + m["Approved_PBs"]
        out["Pending"] = m["Pending_CBE"] + m["Pending_PBs"]
        out["Rejected"] = m["Rejected_CBE"] + m["Rejected_PBs"]
        out["Total_Checked"] = m["Total_Checked_CBE"] + m["Total_Checked_PBs"]

    out["Progress_Percentage"] = np.where(
        out["Total_Sample_Size"] > 0,
        (out["Total_Checked"] / out["Total_Sample_Size"]) * 100.0,
        0
    ).clip(0, 100).round(1)

    out["Progress_Status"] = out["Progress_Percentage"].apply(
        lambda x: "On Track" if x >= 70 else "Behind Schedule" if x >= 40 else "Critical"
    )

    # Add normalized keys for map matching
    out["_prov_norm"] = out["Province"].map(norm_text)
    out["_dist_norm"] = out["District"].map(norm_text)

    return out

@st.cache_data(ttl=600)
def load_google_sheet():
    """
    Reads your Google Sheet using a service account.
    HINT:
      - Put the service account JSON into Streamlit Secrets under 'gcp_service_account'
      - Share the Google Sheet with the service account email (Viewer is enough)
    """
    import gspread
    from google.oauth2.service_account import Credentials

    scopes = ["https://www.googleapis.com/auth/spreadsheets.readonly"]
    creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scopes)
    client = gspread.authorize(creds)

    sh = client.open_by_key(SPREADSHEET_KEY)
    ws = sh.worksheet(WORKSHEET_NAME)
    data = ws.get_all_records()
    df = pd.DataFrame(data)
    df.columns = [str(c).strip() for c in df.columns]
    return df

@st.cache_data(ttl=86400)
def load_geojson(url: str):
    r = requests.get(url, timeout=30)
    r.raise_for_status()
    return r.json()

def prepare_geojson_for_matching(geojson: dict, name_prop: str = "shapeName", new_prop: str = "name_norm") -> dict:
    """
    Add a normalized name property to each feature: properties[name_norm] = norm_text(properties[shapeName]).
    """
    gj = geojson
    for f in gj.get("features", []):
        props = f.get("properties", {})
        raw_name = props.get(name_prop, "")
        props[new_prop] = norm_text(raw_name)
        f["properties"] = props
    return gj

def make_pdf_report(
    tool_choice: str,
    filters: dict,
    kpis: dict,
    regional_summary: pd.DataFrame,
    province_summary: pd.DataFrame,
    comment_summary: dict
) -> bytes:
    """
    Generates a standard, official-looking PDF report.
    Includes 'comments' summary similar to your sample report style.  (See your provided PDF structure.) 
    """
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=1.6*cm,
        rightMargin=1.6*cm,
        topMargin=1.6*cm,
        bottomMargin=1.6*cm
    )
    styles = getSampleStyleSheet()
    story = []

    title = f"Export Report — Sample Track Dashboard ({tool_choice})"
    story.append(Paragraph(title, styles["Title"]))
    story.append(Spacer(1, 10))

    exported_on = datetime.now().strftime("%A, %B %d, %Y, %I:%M %p")
    story.append(Paragraph(f"<b>Exported on:</b> {exported_on}", styles["Normal"]))
    story.append(Paragraph(f"<b>Data source:</b> Google Sheets (Spreadsheet Key: {SPREADSHEET_KEY}, Sheet: {WORKSHEET_NAME})", styles["Normal"]))
    story.append(Spacer(1, 10))

    # Filters
    story.append(Paragraph("<b>Filters applied</b>", styles["Heading3"]))
    filt_tbl = [
        ["Region", filters.get("region", "All")],
        ["Province", filters.get("province", "All")],
        ["District", filters.get("district", "All")],
        ["Progress Status", ", ".join(filters.get("status", ["All"])) if isinstance(filters.get("status"), list) else str(filters.get("status"))],
    ]
    t = Table(filt_tbl, colWidths=[5*cm, 10*cm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.whitesmoke),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.grey),
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    story.append(t)
    story.append(Spacer(1, 12))

    # KPIs
    story.append(Paragraph("<b>Key metrics</b>", styles["Heading3"]))
    kpi_tbl = [
        ["Total Target", f"{kpis['total_sample']:,.0f}"],
        ["Total Received", f"{kpis['total_received']:,.0f}"],
        ["Total Checked", f"{kpis['total_checked']:,.0f}"],
        ["Approved", f"{kpis['total_approved']:,.0f}"],
        ["Rejected", f"{kpis['total_rejected']:,.0f}"],
        ["Pending", f"{kpis['total_pending']:,.0f}"],
        ["Overall Progress (%)", f"{kpis['overall_progress']:.1f}%"],
    ]
    kt = Table(kpi_tbl, colWidths=[7*cm, 8*cm])
    kt.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.3, colors.grey),
        ("BACKGROUND", (0, 0), (-1, 0), colors.whitesmoke),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
    ]))
    story.append(kt)
    story.append(Spacer(1, 12))

    # Comments summary
    story.append(Paragraph("<b>Comments summary</b>", styles["Heading3"]))
    if not comment_summary["comment_cols"]:
        story.append(Paragraph("No comment columns were detected in the sheet.", styles["Normal"]))
    else:
        story.append(Paragraph(f"Detected comment columns: {', '.join([str(c) for c in comment_summary['comment_cols']])}", styles["Normal"]))
        story.append(Paragraph(f"Total non-empty comment entries: <b>{comment_summary['non_empty']:,}</b>", styles["Normal"]))
        if comment_summary["top"]:
            story.append(Spacer(1, 6))
            story.append(Paragraph("Most frequent comments (top 10):", styles["Normal"]))
            top_tbl = [["Comment", "Count"]]
            for txt, cnt in comment_summary["top"]:
                # Keep short to prevent PDF overflow
                short_txt = (txt[:120] + "…") if len(txt) > 120 else txt
                top_tbl.append([short_txt, str(cnt)])
            tt = Table(top_tbl, colWidths=[12*cm, 3*cm])
            tt.setStyle(TableStyle([
                ("GRID", (0, 0), (-1, -1), 0.3, colors.grey),
                ("BACKGROUND", (0, 0), (-1, 0), colors.whitesmoke),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]))
            story.append(tt)

    story.append(Spacer(1, 12))

    # Regional summary
    story.append(Paragraph("<b>Regional summary</b>", styles["Heading3"]))
    if regional_summary.empty:
        story.append(Paragraph("No regional data under selected filters.", styles["Normal"]))
    else:
        rs = regional_summary.copy()
        rs = rs[["Region", "Total_Sample_Size", "Total_Checked", "Approved", "Rejected", "Pending", "Progress"]]
        rs_tbl = [rs.columns.tolist()] + rs.values.tolist()
        rtable = Table(rs_tbl, colWidths=[4*cm, 2.2*cm, 2.2*cm, 1.7*cm, 1.7*cm, 1.7*cm, 1.7*cm])
        rtable.setStyle(TableStyle([
            ("GRID", (0, 0), (-1, -1), 0.3, colors.grey),
            ("BACKGROUND", (0, 0), (-1, 0), colors.whitesmoke),
            ("FONTSIZE", (0, 0), (-1, -1), 7.5),
        ]))
        story.append(rtable)

    story.append(Spacer(1, 12))

    # Province summary (top 20)
    story.append(Paragraph("<b>Province summary (top 20 by progress)</b>", styles["Heading3"]))
    if province_summary.empty:
        story.append(Paragraph("No province data under selected filters.", styles["Normal"]))
    else:
        ps = province_summary.copy().sort_values("Progress", ascending=False).head(20)
        ps = ps[["Province", "Total_Sample_Size", "Total_Checked", "Approved", "Rejected", "Pending", "Progress"]]
        ps_tbl = [ps.columns.tolist()] + ps.values.tolist()
        ptable = Table(ps_tbl, colWidths=[4.3*cm, 2.2*cm, 2.2*cm, 1.6*cm, 1.6*cm, 1.6*cm, 1.6*cm])
        ptable.setStyle(TableStyle([
            ("GRID", (0, 0), (-1, -1), 0.3, colors.grey),
            ("BACKGROUND", (0, 0), (-1, 0), colors.whitesmoke),
            ("FONTSIZE", (0, 0), (-1, -1), 7.5),
        ]))
        story.append(ptable)

    story.append(Spacer(1, 10))
    story.append(Paragraph("<i>Note:</i> This report is generated automatically from the selected tool prefix (CBE-/PBs-/Total-) and the sheet headers.", styles["Normal"]))

    doc.build(story)
    return buffer.getvalue()

# =========================
# Load data
# =========================
st.sidebar.markdown("## Data setup (Hints)")
st.sidebar.caption("Hints:")
st.sidebar.caption("• Put your service account JSON in Streamlit Secrets under: gcp_service_account")
st.sidebar.caption("• Share the Google Sheet with the service account email")
st.sidebar.caption("• Ensure the worksheet tab name is exactly: Test")

try:
    df_sheet = load_google_sheet()
except Exception as e:
    st.error("Google Sheets connection failed.")
    st.markdown("""
**Hints to fix:**
- In Streamlit Cloud → App → Settings → Secrets: add `gcp_service_account` (full JSON)
- Share your Google Sheet with the service account email (Viewer access is enough)
- Confirm the sheet tab name is `Test`
""")
    st.code(str(e))
    st.stop()

# =========================
# Sidebar (NO DATE FILTER)
# =========================
st.sidebar.markdown("## Filters")

tool_choice = st.sidebar.selectbox(
    "Select tool",
    ["Total", "CBE", "PBs"],
    help="Total uses Total- columns if present. If Total- columns are missing, it will try to sum CBE + PBs."
)

# Build dataset from prefixes
try:
    df = build_tool_view(df_sheet, tool_choice)
except Exception as e:
    st.error("Failed to build dataset from sheet headers.")
    st.code(str(e))
    st.stop()

selected_region = st.sidebar.selectbox(
    "Select region",
    ["All"] + sorted(df["Region"].dropna().unique().tolist())
)

if selected_region != "All":
    province_options = ["All"] + sorted(df[df["Region"] == selected_region]["Province"].dropna().unique().tolist())
else:
    province_options = ["All"] + sorted(df["Province"].dropna().unique().tolist())

selected_province = st.sidebar.selectbox("Select province", province_options)

if selected_province != "All":
    district_options = ["All"] + sorted(df[df["Province"] == selected_province]["District"].dropna().unique().tolist())
elif selected_region != "All":
    district_options = ["All"] + sorted(df[df["Region"] == selected_region]["District"].dropna().unique().tolist())
else:
    district_options = ["All"] + sorted(df["District"].dropna().unique().tolist())

selected_district = st.sidebar.selectbox("Select district", district_options)

progress_status = st.sidebar.multiselect(
    "Select progress status",
    options=["All", "On Track", "Behind Schedule", "Critical"],
    default=["All"],
    help="Use this to filter by computed progress status."
)

# Apply filters
filtered_df = df.copy()
if selected_region != "All":
    filtered_df = filtered_df[filtered_df["Region"] == selected_region]
if selected_province != "All":
    filtered_df = filtered_df[filtered_df["Province"] == selected_province]
if selected_district != "All":
    filtered_df = filtered_df[filtered_df["District"] == selected_district]
if "All" not in progress_status:
    filtered_df = filtered_df[filtered_df["Progress_Status"].isin(progress_status)]

# =========================
# KPIs
# =========================
st.markdown('<div class="section-header">Key Performance Indicators</div>', unsafe_allow_html=True)

total_sample = float(filtered_df["Total_Sample_Size"].sum())
total_received = float(filtered_df["Total_Received"].sum())
total_approved = float(filtered_df["Approved"].sum())
total_pending = float(filtered_df["Pending"].sum())
total_rejected = float(filtered_df["Rejected"].sum())
total_checked = float(filtered_df["Total_Checked"].sum())

overall_progress = (total_checked / total_sample * 100.0) if total_sample > 0 else 0.0
rejection_rate = (total_rejected / total_checked * 100.0) if total_checked > 0 else 0.0

k1, k2, k3, k4 = st.columns(4)

with k1:
    st.markdown(f"""
    <div class="metric-card">
        <div class="kpi-label">{tool_choice} — Total Target</div>
        <div class="kpi-value">{total_sample:,.0f}</div>
        <div class="kpi-change">Provinces: {filtered_df["Province"].nunique():,} | Districts: {filtered_df["District"].nunique():,}</div>
    </div>
    """, unsafe_allow_html=True)

with k2:
    st.markdown(f"""
    <div class="metric-card">
        <div class="kpi-label">Overall Progress</div>
        <div class="kpi-value">{overall_progress:.1f}%</div>
        <div class="kpi-change">Checked: {total_checked:,.0f} | Remaining: {max(total_sample-total_checked, 0):,.0f}</div>
    </div>
    """, unsafe_allow_html=True)

with k3:
    st.markdown(f"""
    <div class="metric-card">
        <div class="kpi-label">Approvals</div>
        <div class="kpi-value">{total_approved:,.0f}</div>
        <div class="kpi-change">Rejected: {total_rejected:,.0f}</div>
    </div>
    """, unsafe_allow_html=True)

with k4:
    st.markdown(f"""
    <div class="metric-card">
        <div class="kpi-label">Pending + Rejection Rate</div>
        <div class="kpi-value">{total_pending:,.0f}</div>
        <div class="kpi-change">Rejection rate (of checked): {rejection_rate:.1f}%</div>
    </div>
    """, unsafe_allow_html=True)

# =========================
# Maps
# =========================
st.markdown('<div class="section-header">Maps</div>', unsafe_allow_html=True)
st.markdown('<div class="hint">If the map does not render, it usually means the app cannot download GeoJSON (internet restrictions). See the hint panel below.</div>', unsafe_allow_html=True)

# Load geojson and prepare normalized properties
adm1 = None
adm2 = None
geojson_error = None
try:
    adm1 = load_geojson(ADM1_GEOJSON_URL)
    adm2 = load_geojson(ADM2_GEOJSON_URL)
    adm1 = prepare_geojson_for_matching(adm1, name_prop="shapeName", new_prop="name_norm")
    adm2 = prepare_geojson_for_matching(adm2, name_prop="shapeName", new_prop="name_norm")
except Exception as e:
    geojson_error = str(e)

map_left, map_right = st.columns(2)

# Province summary for national map
prov_summary = filtered_df.groupby(["Province", "_prov_norm"], as_index=False).agg({
    "Total_Sample_Size":"sum",
    "Total_Checked":"sum",
    "Total_Received":"sum",
    "Approved":"sum",
    "Rejected":"sum",
    "Pending":"sum"
})
prov_summary["Progress_Percentage"] = np.where(
    prov_summary["Total_Sample_Size"] > 0,
    (prov_summary["Total_Checked"] / prov_summary["Total_Sample_Size"] * 100.0),
    0
).round(1)

# District summary for provincial map
dist_summary = filtered_df.groupby(["Province", "District", "_dist_norm"], as_index=False).agg({
    "Total_Sample_Size":"sum",
    "Total_Checked":"sum",
    "Total_Received":"sum",
    "Approved":"sum",
    "Rejected":"sum",
    "Pending":"sum"
})
dist_summary["Progress_Percentage"] = np.where(
    dist_summary["Total_Sample_Size"] > 0,
    (dist_summary["Total_Checked"] / dist_summary["Total_Sample_Size"] * 100.0),
    0
).round(1)

with map_left:
    st.markdown("##### Afghanistan (Provinces)")
    if adm1 is None:
        st.warning("Map data could not be loaded.")
        if geojson_error:
            st.code(geojson_error)
        st.markdown("""
**Hint:** If your Streamlit hosting blocks GitHub downloads, the GeoJSON cannot be fetched.
Solution options:
- Allow outbound internet access, or
- Host the GeoJSON on an accessible URL, or
- Upload the GeoJSON files with the app and load locally.
""")
    else:
        fig_afg = px.choropleth(
            prov_summary,
            geojson=adm1,
            locations="_prov_norm",
            featureidkey="properties.name_norm",
            color="Progress_Percentage",
            hover_name="Province",
            hover_data={
                "Progress_Percentage": True,
                "Total_Sample_Size": True,
                "Total_Checked": True,
                "Approved": True,
                "Rejected": True,
                "Pending": True,
                "_prov_norm": False
            },
            title=f"{tool_choice} — Progress by Province"
        )
        fig_afg.update_geos(fitbounds="locations", visible=False)
        fig_afg.update_layout(height=520, margin=dict(l=0, r=0, t=40, b=0))
        st.plotly_chart(fig_afg, use_container_width=True)

with map_right:
    st.markdown("##### Selected Province (Districts)")
    if adm2 is None:
        st.info("Select a province to display district-level map (GeoJSON required).")
    else:
        if selected_province == "All":
            st.info("Please select a province in the sidebar to view the district map.")
        else:
            ds = dist_summary[dist_summary["Province"] == selected_province].copy()
            if ds.empty:
                st.info("No district-level records for the selected province.")
            else:
                fig_dist = px.choropleth(
                    ds,
                    geojson=adm2,
                    locations="_dist_norm",
                    featureidkey="properties.name_norm",
                    color="Progress_Percentage",
                    hover_name="District",
                    hover_data={
                        "Progress_Percentage": True,
                        "Total_Sample_Size": True,
                        "Total_Checked": True,
                        "Total_Received": True,
                        "Approved": True,
                        "Rejected": True,
                        "Pending": True,
                        "_dist_norm": False
                    },
                    title=f"{tool_choice} — District Progress in {selected_province}"
                )
                fig_dist.update_geos(fitbounds="locations", visible=False)
                fig_dist.update_layout(height=520, margin=dict(l=0, r=0, t=40, b=0))
                st.plotly_chart(fig_dist, use_container_width=True)

# =========================
# Overview Charts
# =========================
st.markdown('<div class="section-header">Data Overview</div>', unsafe_allow_html=True)
tab1, tab2, tab3 = st.tabs(["Progress Gauge", "Status Breakdown", "Target vs Checked"])

with tab1:
    fig_g = go.Figure()
    fig_g.add_trace(go.Indicator(
        mode="gauge+number",
        value=float(overall_progress),
        title={'text': f"{tool_choice} — Overall Progress"},
        gauge={
            'axis': {'range': [None, 100]},
            'steps': [
                {'range': [0, 40], 'color': "#FEE2E2"},
                {'range': [40, 70], 'color': "#FEF3C7"},
                {'range': [70, 100], 'color': "#D1FAE5"}
            ],
            'threshold': {'line': {'color': "red", 'width': 4}, 'thickness': 0.75, 'value': 70}
        }
    ))
    fig_g.update_layout(height=320, margin=dict(l=40, r=40, t=60, b=20))
    st.plotly_chart(fig_g, use_container_width=True)

with tab2:
    c1, c2 = st.columns(2)

    with c1:
        status_counts = filtered_df.groupby("Progress_Status").size().reset_index(name="Count")
        if status_counts.empty:
            st.info("No records for selected filters.")
        else:
            fig_pie = px.pie(status_counts, values="Count", names="Progress_Status", hole=0.45, title="Progress Status Distribution")
            st.plotly_chart(fig_pie, use_container_width=True)

    with c2:
        breakdown = pd.DataFrame({
            "Status": ["Approved", "Pending", "Rejected", "Remaining (Target-Checked)"],
            "Count": [total_approved, total_pending, total_rejected, max(total_sample-total_checked, 0)]
        })
        fig_bar = px.bar(breakdown, x="Status", y="Count", title="Review + Remaining Breakdown")
        fig_bar.update_layout(xaxis_title="", yaxis_title="Count")
        st.plotly_chart(fig_bar, use_container_width=True)

with tab3:
    if filtered_df.empty:
        st.info("No records for selected filters.")
    else:
        fig_sc = px.scatter(
            filtered_df,
            x="Total_Sample_Size",
            y="Total_Checked",
            color="Progress_Percentage",
            hover_name="District",
            hover_data=["Province", "Region", "Approved", "Rejected", "Pending", "Total_Received"],
            title=f"{tool_choice} — Target vs Checked (District level)"
        )
        st.plotly_chart(fig_sc, use_container_width=True)

# =========================
# Detailed Tables
# =========================
st.markdown('<div class="section-header">Detailed Analysis</div>', unsafe_allow_html=True)
l, r = st.columns(2)

with l:
    st.markdown("##### Province Summary")
    province_summary = filtered_df.groupby("Province", as_index=False).agg({
        "Total_Sample_Size":"sum",
        "Total_Received":"sum",
        "Total_Checked":"sum",
        "Approved":"sum",
        "Rejected":"sum",
        "Pending":"sum"
    })
    province_summary["Progress"] = np.where(
        province_summary["Total_Sample_Size"] > 0,
        (province_summary["Total_Checked"] / province_summary["Total_Sample_Size"] * 100.0),
        0
    ).round(1)

    st.dataframe(
        province_summary.sort_values("Progress", ascending=False),
        use_container_width=True,
        height=420
    )

with r:
    st.markdown("##### District Summary")
    metric_sort = st.selectbox(
        "Sort districts by",
        ["Progress_Percentage", "Total_Sample_Size", "Total_Checked", "Total_Received", "Approved", "Rejected", "Pending"],
        help="This sorts the district table under current filters."
    )
    district_summary = filtered_df.groupby(["Province", "District"], as_index=False).agg({
        "Total_Sample_Size":"sum",
        "Total_Received":"sum",
        "Total_Checked":"sum",
        "Approved":"sum",
        "Rejected":"sum",
        "Pending":"sum",
        "Progress_Percentage":"mean"
    }).round(2)

    st.dataframe(
        district_summary.sort_values(metric_sort, ascending=False).head(60),
        use_container_width=True,
        height=420
    )

# =========================
# PDF Export (standard naming + include comments summary)
# =========================
st.markdown('<div class="section-header">Export</div>', unsafe_allow_html=True)

comment_summary = summarize_comments(df_sheet)  # read comments from full sheet
regional_summary = filtered_df.groupby("Region", as_index=False).agg({
    "Total_Sample_Size":"sum",
    "Total_Checked":"sum",
    "Approved":"sum",
    "Rejected":"sum",
    "Pending":"sum"
})
regional_summary["Progress"] = np.where(
    regional_summary["Total_Sample_Size"] > 0,
    (regional_summary["Total_Checked"] / regional_summary["Total_Sample_Size"] * 100.0),
    0
).round(1)

filters_for_pdf = {
    "region": selected_region,
    "province": selected_province,
    "district": selected_district,
    "status": progress_status
}
kpis_for_pdf = {
    "total_sample": total_sample,
    "total_received": total_received,
    "total_checked": total_checked,
    "total_approved": total_approved,
    "total_rejected": total_rejected,
    "total_pending": total_pending,
    "overall_progress": overall_progress
}

pdf_col1, pdf_col2 = st.columns([1, 2])

with pdf_col1:
    if st.button("Generate PDF report", use_container_width=True, help="Creates an official PDF export report and includes a comments summary if comment columns exist."):
        pdf_bytes = make_pdf_report(
            tool_choice=tool_choice,
            filters=filters_for_pdf,
            kpis=kpis_for_pdf,
            regional_summary=regional_summary,
            province_summary=province_summary,
            comment_summary=comment_summary
        )
        now_tag = datetime.now().strftime("%Y%m%d_%H%M")
        file_name = f"SampleTrack_{tool_choice}_ExportReport_{now_tag}.pdf"
        st.download_button(
            label="Download PDF",
            data=pdf_bytes,
            file_name=file_name,
            mime="application/pdf",
            use_container_width=True
        )

with pdf_col2:
    st.markdown("""
<div class="hint">
<b>PDF export notes</b><br/>
• The PDF uses a standard formal structure (Exported on, Data source, Filters applied, Key metrics, Comments summary, Regional and Province summaries).<br/>
• Comments are detected automatically from any columns containing "comment" or ending with "-Comments" / "_Comments".<br/>
• If you want specific comment columns to be included, keep their header names consistent (e.g., Total-Comments, CBE-Comments, PBs-Comments).
</div>
""", unsafe_allow_html=True)

# =========================
# Footer
# =========================
st.markdown("---")
st.markdown(
    f"<div class='hint' style='text-align:center;'>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')} | Tool: {tool_choice} | Records: {len(filtered_df):,}</div>",
    unsafe_allow_html=True
)
