import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
import plotly.graph_objects as go
import plotly.express as px
import requests
from io import BytesIO
import json

# PDF generation (ReportLab)
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER

# =========================
# Page Config
# =========================
st.set_page_config(
    page_title="Sample Track Analytics Dashboard",
    page_icon="",
    layout="wide",
    initial_sidebar_state="expanded"
)

# =========================
# Simple Clean CSS (NO emojis)
# =========================
st.markdown("""
<style>
    .app-header {
        font-size: 1.8rem;
        font-weight: 700;
        color: #0f172a;
        margin: 0.25rem 0 1.0rem 0;
        padding: 0.75rem 1rem;
        background: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 12px;
    }
    .section-title{
        font-size: 1.2rem;
        font-weight: 700;
        color: #0f172a;
        margin-top: 1.2rem;
        margin-bottom: 0.6rem;
    }
    .kpi-card{
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 14px;
        padding: 14px 16px;
        box-shadow: 0 1px 2px rgba(15,23,42,0.04);
        height: 118px;
    }
    .kpi-label{
        font-size: 0.85rem;
        color: #475569;
        font-weight: 600;
        margin-bottom: 6px;
    }
    .kpi-value{
        font-size: 1.8rem;
        font-weight: 800;
        color: #0f172a;
        line-height: 1.1;
        margin-bottom: 4px;
    }
    .kpi-sub{
        font-size: 0.85rem;
        color: #64748b;
        font-weight: 600;
    }
    .hint{
        background: #f8fafc;
        border: 1px solid #e2e8f0;
        border-left: 4px solid #3b82f6;
        border-radius: 10px;
        padding: 10px 12px;
        color: #334155;
        font-size: 0.9rem;
    }
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="app-header">Sample Track Analytics Dashboard</div>', unsafe_allow_html=True)

# =========================
# Google Sheet Config
# =========================
SPREADSHEET_KEY = "1lkztBZ4eG1BQx-52XgnA6w8YIiw-Sm85pTlQQziurfw"
WORKSHEET_NAME = "Test"

# =========================
# Text Normalization
# =========================
def norm_text(x: str) -> str:
    s = str(x).strip().lower()
    s = s.replace("_", " ").replace("'", "").replace("`", "")
    s = " ".join(s.split())
    s = s.replace("sar e pul", "sar-e-pul")
    s = s.replace("sare pul", "sar-e-pul")
    s = s.replace("maidan wardak", "wardak")
    s = s.replace("maydan wardak", "wardak")
    return s

def remove_total_rows(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    for c in ["Region", "Province", "District"]:
        if c in df.columns:
            df[c] = df[c].astype(str).str.strip()
            df = df[~df[c].str.contains(r"\btotal\b", case=False, na=False)]
    return df

def safe_num(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce").fillna(0)

def find_prefixed_metric(df_cols, prefix, keywords):
    cols = [str(c).strip() for c in df_cols]
    candidates = [c for c in cols if c.startswith(prefix)]
    for kw in keywords:
        for c in candidates:
            if kw.lower() in c.lower():
                return c
    if len(candidates) == 1:
        return candidates[0]
    return None

def build_tool_view(df_raw: pd.DataFrame, tool: str) -> pd.DataFrame:
    df = df_raw.copy()
    if df.shape[1] < 3:
        raise ValueError("The sheet must have at least 3 columns (Region, Province, District).")

    cols = list(df.columns)
    df = df.rename(columns={cols[0]: "Region", cols[1]: "Province", cols[2]: "District"})

    df["Region"] = df["Region"].astype(str).str.strip()
    df["Province"] = df["Province"].astype(str).str.strip()
    df["District"] = df["District"].astype(str).str.strip()

    df = remove_total_rows(df)

    prefix_map = {"CBE": "CBE-", "PBs": "PBs-", "Total": "Total-"}
    prefix = prefix_map[tool]

    col_target = find_prefixed_metric(df.columns, prefix, ["target", "sample", "samplesize"])
    col_received = find_prefixed_metric(df.columns, prefix, ["received", "collected"])
    col_approved = find_prefixed_metric(df.columns, prefix, ["approved", "approve"])
    col_pending = find_prefixed_metric(df.columns, prefix, ["pending", "review"])
    col_rejected = find_prefixed_metric(df.columns, prefix, ["rejected", "reject"])
    col_checked = find_prefixed_metric(df.columns, prefix, ["checked", "reviewed"])

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

    # If Total- is not present, compute Total = CBE + PBs
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
        lambda x: "On Track" if x >= 75 else "Behind Schedule" if x >= 50 else "Critical"
    )

    out["_prov_norm"] = out["Province"].map(norm_text)
    out["_dist_norm"] = out["District"].map(norm_text)
    return out

# =========================
# Google Sheet loader
# =========================
@st.cache_data(ttl=600)
def load_google_sheet():
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

# =========================
# GeoJSON via geoBoundaries API (ADM1 + ADM2)
# =========================
@st.cache_data(ttl=86400)
def fetch_geoboundaries_geojson(adm_level="ADM1", release="gbOpen", iso="AFG", simplified=True, timeout=60):
    """
    Reliable geoBoundaries downloader.
    Returns GeoJSON (FeatureCollection).
    """
    api_url = f"https://www.geoboundaries.org/api/current/{release}/{iso}/{adm_level}/"
    meta_resp = requests.get(api_url, timeout=timeout)
    meta_resp.raise_for_status()
    meta = meta_resp.json()
    if isinstance(meta, list) and len(meta) > 0:
        meta = meta[0]

    # pick a download URL
    geo_url = meta.get("simplifiedGeometryGeoJSON") if simplified else meta.get("gjDownloadURL")
    if not geo_url:
        geo_url = meta.get("gjDownloadURL")
    if not geo_url:
        return {"type": "FeatureCollection", "features": []}

    g = requests.get(geo_url, timeout=timeout)
    g.raise_for_status()

    # ensure it's JSON (not HTML)
    txt = g.text.strip()
    if not (txt.startswith("{") or txt.startswith("[")):
        raise ValueError("GeoJSON download did not return JSON (blocked or redirected).")

    return g.json()

def prepare_geojson_for_matching(geojson: dict, name_candidates=("shapeName", "NAME_1", "NAME", "name")) -> dict:
    for f in geojson.get("features", []):
        props = f.get("properties", {})
        raw_name = ""
        for k in name_candidates:
            if k in props and props.get(k):
                raw_name = props.get(k)
                break
        props["name_norm"] = norm_text(raw_name)
        f["properties"] = props
    return geojson

# =========================
# Helper: choose property key for Plotly featureidkey
# =========================
def detect_featureidkey(geojson: dict, expected_prop="name_norm"):
    """
    Ensures we know where properties are stored.
    We always set properties.name_norm in prepare_geojson_for_matching,
    so featureidkey should be 'properties.name_norm'.
    """
    return "properties.name_norm"

# =========================
# PDF Report (NO comments)
# =========================
def make_pdf_report(tool_choice: str, filters: dict, kpis: dict,
                    regional_summary: pd.DataFrame, province_summary: pd.DataFrame,
                    filtered_df: pd.DataFrame) -> bytes:
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=1.5*cm,
        rightMargin=1.5*cm,
        topMargin=1.5*cm,
        bottomMargin=1.5*cm
    )

    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        name="TitleMain",
        parent=styles["Title"],
        fontSize=18,
        textColor=colors.HexColor("#0f172a"),
        alignment=TA_CENTER,
        spaceAfter=18
    ))
    styles.add(ParagraphStyle(
        name="H2",
        parent=styles["Heading2"],
        fontSize=12,
        textColor=colors.HexColor("#0f172a"),
        spaceBefore=12,
        spaceAfter=8
    ))
    styles.add(ParagraphStyle(
        name="Small",
        parent=styles["Normal"],
        fontSize=9,
        textColor=colors.HexColor("#334155"),
        leading=12
    ))

    story = []
    now_txt = datetime.now().strftime("%Y-%m-%d %H:%M")

    story.append(Paragraph("SAMPLE TRACK ANALYTICS REPORT", styles["TitleMain"]))
    story.append(Paragraph(f"Tool: {tool_choice}", styles["Small"]))
    story.append(Paragraph(f"Generated on: {now_txt}", styles["Small"]))
    story.append(Spacer(1, 0.6*cm))

    story.append(Paragraph("Filters", styles["H2"]))
    f_rows = [
        ["Region", filters.get("region", "All")],
        ["Province", filters.get("province", "All")],
        ["District", filters.get("district", "All")],
        ["Progress Status", ", ".join(filters.get("status", ["All"]))],
    ]
    ft = Table([["Filter", "Value"]] + f_rows, colWidths=[4*cm, 11*cm])
    ft.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#f1f5f9")),
        ("TEXTCOLOR", (0,0), (-1,0), colors.HexColor("#0f172a")),
        ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTSIZE", (0,0), (-1,-1), 9),
        ("GRID", (0,0), (-1,-1), 0.3, colors.HexColor("#cbd5e1")),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
    ]))
    story.append(ft)
    story.append(Spacer(1, 0.6*cm))

    story.append(Paragraph("Executive Summary", styles["H2"]))
    es = [
        ["Metric", "Value"],
        ["Total Target", f"{kpis['total_sample']:,.0f}"],
        ["Total Received", f"{kpis['total_received']:,.0f}"],
        ["Total Checked", f"{kpis['total_checked']:,.0f}"],
        ["Approved", f"{kpis['total_approved']:,.0f}"],
        ["Rejected", f"{kpis['total_rejected']:,.0f}"],
        ["Pending", f"{kpis['total_pending']:,.0f}"],
        ["Overall Progress", f"{kpis['overall_progress']:.1f}%"],
        ["Coverage", f"{filtered_df['Province'].nunique()} Provinces / {filtered_df['District'].nunique()} Districts"],
    ]
    est = Table(es, colWidths=[6*cm, 9*cm])
    est.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#0f172a")),
        ("TEXTCOLOR", (0,0), (-1,0), colors.white),
        ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTSIZE", (0,0), (-1,-1), 9),
        ("GRID", (0,0), (-1,-1), 0.3, colors.HexColor("#cbd5e1")),
        ("BACKGROUND", (0,1), (-1,-1), colors.HexColor("#ffffff")),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
    ]))
    story.append(est)

    story.append(Spacer(1, 0.4*cm))
    story.append(Paragraph("Regional Performance", styles["H2"]))
    if regional_summary is None or regional_summary.empty:
        story.append(Paragraph("No data available for the selected filters.", styles["Small"]))
    else:
        rs = [["Region", "Target", "Checked", "Progress %"]] + [
            [r["Region"], f"{r['Total_Sample_Size']:,.0f}", f"{r['Total_Checked']:,.0f}", f"{r['Progress']:.1f}%"]
            for _, r in regional_summary.iterrows()
        ]
        rst = Table(rs, colWidths=[5*cm, 3.2*cm, 3.2*cm, 3.6*cm])
        rst.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#f1f5f9")),
            ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
            ("FONTSIZE", (0,0), (-1,-1), 9),
            ("GRID", (0,0), (-1,-1), 0.3, colors.HexColor("#cbd5e1")),
            ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ]))
        story.append(rst)

    story.append(Spacer(1, 0.4*cm))
    story.append(Paragraph("Top Provinces by Progress", styles["H2"]))
    if province_summary is None or province_summary.empty:
        story.append(Paragraph("No province summary available.", styles["Small"]))
    else:
        top = province_summary.sort_values("Progress", ascending=False).head(10)
        ps = [["Province", "Progress %", "Checked", "Approved", "Rejected"]] + [
            [r["Province"], f"{r['Progress']:.1f}%", f"{r['Total_Checked']:,.0f}", f"{r['Approved']:,.0f}", f"{r['Rejected']:,.0f}"]
            for _, r in top.iterrows()
        ]
        pst = Table(ps, colWidths=[5.2*cm, 2.6*cm, 2.6*cm, 2.4*cm, 2.2*cm])
        pst.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#f1f5f9")),
            ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
            ("FONTSIZE", (0,0), (-1,-1), 9),
            ("GRID", (0,0), (-1,-1), 0.3, colors.HexColor("#cbd5e1")),
            ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ]))
        story.append(pst)

    story.append(Spacer(1, 0.8*cm))
    story.append(Paragraph("End of Report", styles["Small"]))

    doc.build(story)
    return buffer.getvalue()

# =========================
# Load data
# =========================
try:
    df_sheet = load_google_sheet()
    if df_sheet.empty:
        st.error("Google Sheet is empty.")
        st.stop()
except Exception:
    st.error("Failed to load data from Google Sheet. Check service account in Streamlit secrets.")
    st.stop()

# =========================
# Sidebar
# =========================
st.sidebar.markdown("Filters & Controls")

tool_choice = st.sidebar.selectbox(
    "Select Monitoring Tool",
    ["Total", "CBE", "PBs"],
    help="Choose which columns to analyze based on the prefix (CBE-, PBs-, Total-)."
)

try:
    df = build_tool_view(df_sheet, tool_choice)
except Exception as e:
    st.error(f"Error processing data: {e}")
    st.stop()

selected_region = st.sidebar.selectbox("Select Region", ["All"] + sorted(df["Region"].dropna().unique().tolist()))

if selected_region != "All":
    province_options = ["All"] + sorted(df[df["Region"] == selected_region]["Province"].dropna().unique().tolist())
else:
    province_options = ["All"] + sorted(df["Province"].dropna().unique().tolist())
selected_province = st.sidebar.selectbox("Select Province", province_options)

if selected_province != "All":
    district_options = ["All"] + sorted(df[df["Province"] == selected_province]["District"].dropna().unique().tolist())
elif selected_region != "All":
    district_options = ["All"] + sorted(df[df["Region"] == selected_region]["District"].dropna().unique().tolist())
else:
    district_options = ["All"] + sorted(df["District"].dropna().unique().tolist())
selected_district = st.sidebar.selectbox("Select District", district_options)

progress_status = st.sidebar.multiselect(
    "Progress Status",
    options=["All", "On Track", "Behind Schedule", "Critical"],
    default=["All"]
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
st.markdown('<div class="section-title">Performance Overview</div>', unsafe_allow_html=True)

total_sample = float(filtered_df["Total_Sample_Size"].sum())
total_received = float(filtered_df["Total_Received"].sum())
total_approved = float(filtered_df["Approved"].sum())
total_pending = float(filtered_df["Pending"].sum())
total_rejected = float(filtered_df["Rejected"].sum())
total_checked = float(filtered_df["Total_Checked"].sum())

overall_progress = (total_checked / total_sample * 100.0) if total_sample > 0 else 0.0
approval_rate = (total_approved / total_checked * 100.0) if total_checked > 0 else 0.0
rejection_rate = (total_rejected / total_checked * 100.0) if total_checked > 0 else 0.0

c1, c2, c3, c4 = st.columns(4)
with c1:
    st.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-label">Total Target</div>
        <div class="kpi-value">{total_sample:,.0f}</div>
        <div class="kpi-sub">Provinces: {filtered_df["Province"].nunique():,} | Districts: {filtered_df["District"].nunique():,}</div>
    </div>
    """, unsafe_allow_html=True)

with c2:
    st.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-label">Overall Progress</div>
        <div class="kpi-value">{overall_progress:.1f}%</div>
        <div class="kpi-sub">Checked: {total_checked:,.0f} | Remaining: {max(total_sample-total_checked, 0):,.0f}</div>
    </div>
    """, unsafe_allow_html=True)

with c3:
    st.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-label">Approvals</div>
        <div class="kpi-value">{total_approved:,.0f}</div>
        <div class="kpi-sub">Approval Rate: {approval_rate:.1f}%</div>
    </div>
    """, unsafe_allow_html=True)

with c4:
    st.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-label">Rejections / Pending</div>
        <div class="kpi-value">{total_rejected:,.0f} / {total_pending:,.0f}</div>
        <div class="kpi-sub">Rejection Rate: {rejection_rate:.1f}% | Received: {total_received:,.0f}</div>
    </div>
    """, unsafe_allow_html=True)

# =========================
# Maps (ADM1 + ADM2)
# =========================
st.markdown('<div class="section-title">Geographic Analysis</div>', unsafe_allow_html=True)

# Load GeoJSON (ADM1 + ADM2) using your requested function style
with st.spinner("Loading boundary layers (ADM1 and ADM2)..."):
    try:
        adm1_geojson = fetch_geoboundaries_geojson("ADM1", simplified=True)  # provinces
        adm2_geojson = fetch_geoboundaries_geojson("ADM2", simplified=True)  # districts
        adm1_geojson = prepare_geojson_for_matching(adm1_geojson)
        adm2_geojson = prepare_geojson_for_matching(adm2_geojson, name_candidates=("shapeName", "NAME_2", "NAME", "name"))
    except Exception as e:
        st.error(f"Map layers could not be loaded. {e}")
        adm1_geojson = {"type": "FeatureCollection", "features": []}
        adm2_geojson = {"type": "FeatureCollection", "features": []}

# Province map (Afghanistan)
if adm1_geojson.get("features"):
    prov_summary = filtered_df.groupby(["Province", "_prov_norm"], as_index=False).agg({
        "Total_Sample_Size":"sum",
        "Total_Checked":"sum",
        "Approved":"sum",
        "Rejected":"sum",
        "Pending":"sum"
    })
    prov_summary["Progress_Percentage"] = np.where(
        prov_summary["Total_Sample_Size"] > 0,
        (prov_summary["Total_Checked"] / prov_summary["Total_Sample_Size"]) * 100.0,
        0
    ).round(1)

    fig_afg = px.choropleth(
        prov_summary,
        geojson=adm1_geojson,
        locations="_prov_norm",
        featureidkey="properties.name_norm",
        color="Progress_Percentage",
        hover_name="Province",
        hover_data={
            "Progress_Percentage": ":.1f",
            "Total_Sample_Size": ":,.0f",
            "Total_Checked": ":,.0f",
            "Approved": ":,.0f",
            "Rejected": ":,.0f",
            "Pending": ":,.0f",
            "_prov_norm": False
        },
        color_continuous_scale="RdYlGn",
        range_color=[0, 100],
        title=""
    )
    fig_afg.update_geos(fitbounds="locations", visible=False)
    fig_afg.update_layout(height=520, margin=dict(l=0, r=0, t=10, b=0))
    st.plotly_chart(fig_afg, use_container_width=True)
else:
    st.warning("ADM1 map is not available (empty GeoJSON). Check outbound internet access.")

# District map inside selected province
st.markdown('<div class="section-title">Selected Province - District Level (ADM2)</div>', unsafe_allow_html=True)

if selected_province != "All" and adm2_geojson.get("features"):
    # Prepare district summary for the selected province only
    df_prov = filtered_df[filtered_df["Province"] == selected_province].copy()

    dist_summary = df_prov.groupby(["District", "_dist_norm"], as_index=False).agg({
        "Total_Sample_Size":"sum",
        "Total_Checked":"sum",
        "Approved":"sum",
        "Rejected":"sum",
        "Pending":"sum"
    })
    dist_summary["Progress_Percentage"] = np.where(
        dist_summary["Total_Sample_Size"] > 0,
        (dist_summary["Total_Checked"] / dist_summary["Total_Sample_Size"]) * 100.0,
        0
    ).round(1)

    # IMPORTANT:
    # ADM2 polygons include province + district names. Some datasets store only district names,
    # others store full names. We match by district name normalization via properties.name_norm.
    fig_adm2 = px.choropleth(
        dist_summary,
        geojson=adm2_geojson,
        locations="_dist_norm",
        featureidkey="properties.name_norm",
        color="Progress_Percentage",
        hover_name="District",
        hover_data={
            "Progress_Percentage": ":.1f",
            "Total_Sample_Size": ":,.0f",
            "Total_Checked": ":,.0f",
            "Approved": ":,.0f",
            "Rejected": ":,.0f",
            "Pending": ":,.0f",
            "_dist_norm": False
        },
        color_continuous_scale="RdYlGn",
        range_color=[0, 100],
        title=""
    )

    # Fit map to the selected districts (if found)
    fig_adm2.update_geos(fitbounds="locations", visible=False)
    fig_adm2.update_layout(height=520, margin=dict(l=0, r=0, t=10, b=0))
    st.plotly_chart(fig_adm2, use_container_width=True)

elif selected_province == "All":
    st.info("Select a Province from the sidebar to see district-level map.")
else:
    st.warning("ADM2 map is not available (empty GeoJSON).")

# =========================
# Charts (NO lowess)
# =========================
st.markdown('<div class="section-title">Charts</div>', unsafe_allow_html=True)

t1, t2, t3 = st.tabs(["Status Breakdown", "Region Comparison", "Target vs Checked"])

with t1:
    status_data = pd.DataFrame({
        "Category": ["Approved", "Pending", "Rejected", "Not Checked"],
        "Count": [total_approved, total_pending, total_rejected, max(total_sample-total_checked, 0)]
    })
    fig_bar = px.bar(status_data, x="Category", y="Count", text="Count")
    fig_bar.update_traces(texttemplate="%{text:,}", textposition="outside")
    fig_bar.update_layout(height=420, xaxis_title="", yaxis_title="Count", showlegend=False)
    st.plotly_chart(fig_bar, use_container_width=True)

with t2:
    regional_summary = filtered_df.groupby("Region", as_index=False).agg({
        "Total_Sample_Size":"sum",
        "Total_Checked":"sum",
        "Approved":"sum",
        "Rejected":"sum",
        "Pending":"sum"
    })
    regional_summary["Progress"] = np.where(
        regional_summary["Total_Sample_Size"] > 0,
        (regional_summary["Total_Checked"] / regional_summary["Total_Sample_Size"]) * 100.0,
        0
    ).round(1)

    fig_region = px.bar(regional_summary, x="Region", y="Progress", text="Progress")
    fig_region.update_traces(texttemplate="%{text:.1f}%", textposition="outside")
    fig_region.update_layout(height=420, xaxis_title="", yaxis_title="Progress (%)")
    st.plotly_chart(fig_region, use_container_width=True)

with t3:
    if not filtered_df.empty:
        fig_scatter = px.scatter(
            filtered_df,
            x="Total_Sample_Size",
            y="Total_Checked",
            size="Total_Sample_Size",
            color="Progress_Percentage",
            hover_name="District",
            hover_data=["Province", "Approved", "Rejected", "Pending"],
            size_max=28
        )
        max_val = max(filtered_df["Total_Sample_Size"].max(), filtered_df["Total_Checked"].max())
        fig_scatter.add_trace(go.Scatter(
            x=[0, max_val],
            y=[0, max_val],
            mode="lines",
            name="Target = Checked",
            line=dict(dash="dash")
        ))
        fig_scatter.update_layout(height=520, xaxis_title="Target", yaxis_title="Checked")
        st.plotly_chart(fig_scatter, use_container_width=True)

# =========================
# Tables
# =========================
st.markdown('<div class="section-title">Tables</div>', unsafe_allow_html=True)

left, right = st.columns(2)

with left:
    st.subheader("Province Summary")
    province_summary = filtered_df.groupby("Province", as_index=False).agg({
        "Total_Sample_Size":"sum",
        "Total_Received":"sum",
        "Total_Checked":"sum",
        "Approved":"sum",
        "Rejected":"sum",
        "Pending":"sum",
        "Progress_Percentage":"mean"
    })
    province_summary["Progress"] = province_summary["Progress_Percentage"].round(1)
    province_summary["Approval_Rate"] = np.where(
        province_summary["Total_Checked"] > 0,
        (province_summary["Approved"] / province_summary["Total_Checked"]) * 100.0,
        0
    ).round(1)

    st.dataframe(
        province_summary.sort_values("Progress", ascending=False),
        use_container_width=True,
        height=420
    )

with right:
    st.subheader("District Performance")
    district_summary = filtered_df.groupby(["Province", "District"], as_index=False).agg({
        "Total_Sample_Size":"sum",
        "Total_Checked":"sum",
        "Approved":"sum",
        "Rejected":"sum",
        "Pending":"sum",
        "Progress_Percentage":"mean"
    }).round(1)
    st.dataframe(
        district_summary.sort_values("Progress_Percentage", ascending=False).head(30),
        use_container_width=True,
        height=420
    )

# =========================
# PDF Export
# =========================
st.markdown('<div class="section-title">Report Export</div>', unsafe_allow_html=True)

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

colA, colB = st.columns([1, 2])

with colA:
    if st.button("Generate PDF Report", type="primary", use_container_width=True):
        try:
            pdf_bytes = make_pdf_report(
                tool_choice=tool_choice,
                filters=filters_for_pdf,
                kpis=kpis_for_pdf,
                regional_summary=regional_summary,
                province_summary=province_summary,
                filtered_df=filtered_df
            )
            filename = f"SampleTrack_Report_{tool_choice}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            st.download_button(
                "Download PDF",
                data=pdf_bytes,
                file_name=filename,
                mime="application/pdf",
                use_container_width=True
            )
        except Exception as e:
            st.error(f"Error generating PDF: {e}")

with colB:
    st.markdown("""
    <div class="hint">
    This PDF includes a cover section, filters, executive summary KPIs, regional performance, and top provinces.
    </div>
    """, unsafe_allow_html=True)

# =========================
# Footer
# =========================
st.markdown("---")
st.caption(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | Tool: {tool_choice} | Records: {len(filtered_df):,}")
