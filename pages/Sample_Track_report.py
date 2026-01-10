import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
import plotly.graph_objects as go
import plotly.express as px
import requests

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
# Custom CSS
# =========================
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: 700;
        color: #1E3A8A;
        margin-bottom: 1rem;
        text-align: center;
        padding: 1rem;
        background: linear-gradient(90deg, #EFF6FF, #DBEAFE);
        border-radius: 10px;
        border-left: 6px solid #3B82F6;
    }
    .section-header {
        font-size: 1.8rem;
        font-weight: 600;
        color: #1E40AF;
        margin-top: 1.5rem;
        margin-bottom: 1rem;
        padding-bottom: 0.5rem;
        border-bottom: 3px solid #60A5FA;
    }
    .metric-card {
        background: linear-gradient(135deg, #F0F9FF, #E0F2FE);
        padding: 1.5rem;
        border-radius: 15px;
        border-left: 5px solid #0EA5E9;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05);
        transition: transform 0.3s ease;
    }
    .metric-card:hover { transform: translateY(-5px); box-shadow: 0 8px 12px rgba(0, 0, 0, 0.1); }
    .kpi-label { font-size: 0.9rem; font-weight: 500; color: #475569; text-transform: uppercase; letter-spacing: 0.5px; }
    .kpi-value { font-size: 2.2rem; font-weight: 700; color: #1E3A8A; margin: 0.5rem 0; }
    .kpi-change { font-size: 0.85rem; font-weight: 500; }
    .positive { color: #059669; }
    .negative { color: #DC2626; }
    .neutral  { color: #6B7280; }

    .stTabs [data-baseweb="tab-list"] { gap: 8px; }
    .stTabs [data-baseweb="tab"] { border-radius: 8px 8px 0 0; padding: 10px 20px; background-color: #F3F4F6; }
    .stTabs [aria-selected="true"] { background-color: #3B82F6 !important; color: white !important; }
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-header">📊 Sample Track Analytics Dashboard</div>', unsafe_allow_html=True)

# =========================
# Google Sheet Config
# =========================
SPREADSHEET_KEY = "https://docs.google.com/spreadsheets/d/1lkztBZ4eG1BQx-52XgnA6w8YIiw-Sm85pTlQQziurfw/edit?gid=1114674433#gid=1114674433"
WORKSHEET_NAME = "Test"

# =========================
# GeoJSON sources (Afghanistan)
# =========================
ADM1_GEOJSON_URL = "https://raw.githubusercontent.com/wmgeolab/geoBoundaries/9469f09/releaseData/gbOpen/AFG/ADM1/geoBoundaries-AFG-ADM1.geojson"
ADM2_GEOJSON_URL = "https://raw.githubusercontent.com/wmgeolab/geoBoundaries/9469f09/releaseData/gbOpen/AFG/ADM2/geoBoundaries-AFG-ADM2_simplified.geojson"

# =========================
# Helpers
# =========================
def norm(s):
    return str(s).strip()

def remove_total_rows(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    for c in ["Region", "Province", "District"]:
        if c in df.columns:
            df[c] = df[c].astype(str).str.strip()
            df = df[~df[c].str.contains(r"\btotal\b", case=False, na=False)]
    return df

def to_numeric(df: pd.DataFrame, cols):
    df = df.copy()
    for c in cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)
    return df

def pick_prefixed_col(columns, prefix, keywords):
    """
    columns: list[str]
    prefix: 'CBE-' or 'PBs-' or 'Total-'
    keywords: list[str] (e.g. ['target','sample'])
    """
    cols = [norm(c) for c in columns]
    # exact prefix match first
    candidates = [c for c in cols if c.startswith(prefix)]
    # keyword match
    for kw in keywords:
        for c in candidates:
            if kw.lower() in c.lower():
                return c
    # fallback: if only one candidate and one keyword group
    if len(candidates) == 1:
        return candidates[0]
    return None

def build_tool_view(df_raw: pd.DataFrame, tool: str) -> pd.DataFrame:
    """
    tool: 'CBE' or 'PBs' or 'Total'
    Logic:
      - Column A,B,C are Region/Province/District (use them directly)
      - Metrics are decided by labels:
          CBE-* belongs to CBE
          PBs-* belongs to PBs
          Total-* is general (for Total tool)
    Returns a unified df with standard columns:
      Region, Province, District,
      Total_Sample_Size, Total_Received, Approved, Pending, Rejected, Total_Checked, Progress_Percentage
    """
    df = df_raw.copy()

    # Ensure A/B/C as Region/Province/District by POSITION (as you requested)
    # If sheet already has those names, this keeps them; otherwise force by first 3 columns.
    cols = list(df.columns)
    if len(cols) >= 3:
        df = df.rename(columns={cols[0]: "Region", cols[1]: "Province", cols[2]: "District"})
    else:
        raise ValueError("Sheet must have at least 3 columns: Region, Province, District (A, B, C).")

    for c in ["Region", "Province", "District"]:
        df[c] = df[c].astype(str).str.strip()

    # Remove Total rows (Province Total / District Total etc.)
    df = remove_total_rows(df)

    # tool prefix
    prefix = {"CBE": "CBE-", "PBs": "PBs-", "Total": "Total-"}[tool]

    # Resolve metric columns based on labels in sheet
    all_cols = list(df.columns)

    col_target   = pick_prefixed_col(all_cols, prefix, ["target", "sample", "samplesize", "sample_size", "total_sample"])
    col_received = pick_prefixed_col(all_cols, prefix, ["received", "data_received", "collection", "collected"])
    col_approved = pick_prefixed_col(all_cols, prefix, ["approved", "approve"])
    col_pending  = pick_prefixed_col(all_cols, prefix, ["pending", "review", "in_review", "under_review"])
    col_rejected = pick_prefixed_col(all_cols, prefix, ["rejected", "reject"])
    col_checked  = pick_prefixed_col(all_cols, prefix, ["checked", "reviewed", "total_checked"])

    # Build unified numeric columns (missing ones become 0)
    def get_series(colname):
        if colname and colname in df.columns:
            return pd.to_numeric(df[colname], errors="coerce").fillna(0)
        return pd.Series([0]*len(df), index=df.index, dtype=float)

    df_u = df[["Region","Province","District"]].copy()
    df_u["Total_Sample_Size"] = get_series(col_target)
    df_u["Total_Received"]    = get_series(col_received)
    df_u["Approved"]          = get_series(col_approved)
    df_u["Pending"]           = get_series(col_pending)
    df_u["Rejected"]          = get_series(col_rejected)

    # Total_Checked priority: explicit column if exists, else Approved+Pending+Rejected
    checked_explicit = get_series(col_checked)
    df_u["Total_Checked"] = np.where(checked_explicit > 0, checked_explicit, df_u["Approved"] + df_u["Pending"] + df_u["Rejected"])

    # If Total tool but Total-* columns are not provided, fallback = CBE + PBs
    if tool == "Total" and df_u["Total_Sample_Size"].sum() == 0:
        # sum from CBE and PBs if available
        cbe_df = build_tool_view(df_raw, "CBE")
        pbs_df = build_tool_view(df_raw, "PBs")
        key = ["Region","Province","District"]
        merged = cbe_df.merge(pbs_df, on=key, how="outer", suffixes=("_CBE","_PBs")).fillna(0)
        out = merged[key].copy()
        out["Total_Sample_Size"] = merged["Total_Sample_Size_CBE"] + merged["Total_Sample_Size_PBs"]
        out["Total_Received"]    = merged["Total_Received_CBE"] + merged["Total_Received_PBs"]
        out["Approved"]          = merged["Approved_CBE"] + merged["Approved_PBs"]
        out["Pending"]           = merged["Pending_CBE"] + merged["Pending_PBs"]
        out["Rejected"]          = merged["Rejected_CBE"] + merged["Rejected_PBs"]
        out["Total_Checked"]     = merged["Total_Checked_CBE"] + merged["Total_Checked_PBs"]
        df_u = out

    # Progress %
    df_u["Progress_Percentage"] = np.where(
        df_u["Total_Sample_Size"] > 0,
        (df_u["Total_Checked"] / df_u["Total_Sample_Size"] * 100),
        0
    ).clip(0, 100).round(1)

    df_u["Progress_Status"] = df_u["Progress_Percentage"].apply(
        lambda x: "On Track" if x >= 70 else "Behind Schedule" if x >= 40 else "Critical"
    )

    # Make numeric safe
    df_u = to_numeric(df_u, ["Total_Sample_Size","Total_Received","Approved","Pending","Rejected","Total_Checked","Progress_Percentage"])
    return df_u

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
    df.columns = [norm(c) for c in df.columns]
    return df

@st.cache_data(ttl=86400)
def load_geojson(url: str):
    r = requests.get(url, timeout=30)
    r.raise_for_status()
    return r.json()

# =========================
# Load data
# =========================
try:
    df_sheet = load_google_sheet()
except Exception as e:
    st.error("❌ اتصال به Google Sheet مشکل دارد. این موارد را چک کن:")
    st.markdown("""
- در Streamlit Secrets کل JSON سرویس اکانت را زیر **gcp_service_account** گذاشته باشی
- شیت را با ایمیل Service Account **Share** کرده باشی
- نام ورکشیت دقیقاً **Test** باشد
""")
    st.code(str(e))
    st.stop()

# =========================
# Sidebar Filters (NO DATE FILTER)
# =========================
st.sidebar.markdown("## 🎯 Filters")

# Tool selector (CBE vs PBs vs Total)
st.sidebar.markdown("### 🧰 Tool")
tool_choice = st.sidebar.selectbox("Select Tool", ["Total", "CBE", "PBs"])

# Build view based on labels/prefix
try:
    df = build_tool_view(df_sheet, tool_choice)
except Exception as e:
    st.error("❌ ساختن دیتاست بر اساس لیبل‌های شیت مشکل دارد.")
    st.code(str(e))
    st.stop()

# Region/Province/District filters
st.sidebar.markdown("### 🌍 Region")
regions = ["All"] + sorted(df["Region"].dropna().unique().tolist())
selected_region = st.sidebar.selectbox("Select Region", regions)

st.sidebar.markdown("### 🏙️ Province")
if selected_region != "All":
    provs = ["All"] + sorted(df[df["Region"] == selected_region]["Province"].dropna().unique().tolist())
else:
    provs = ["All"] + sorted(df["Province"].dropna().unique().tolist())
selected_province = st.sidebar.selectbox("Select Province", provs)

st.sidebar.markdown("### 🏘️ District")
if selected_province != "All":
    dists = ["All"] + sorted(df[df["Province"] == selected_province]["District"].dropna().unique().tolist())
elif selected_region != "All":
    dists = ["All"] + sorted(df[df["Region"] == selected_region]["District"].dropna().unique().tolist())
else:
    dists = ["All"] + sorted(df["District"].dropna().unique().tolist())
selected_district = st.sidebar.selectbox("Select District", dists)

st.sidebar.markdown("### 📈 Progress Status")
progress_status = st.sidebar.multiselect(
    "Select Progress Status",
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
st.markdown('<div class="section-header">📈 Key Performance Indicators</div>', unsafe_allow_html=True)

total_sample   = float(filtered_df["Total_Sample_Size"].sum())
total_received = float(filtered_df["Total_Received"].sum())
total_approved = float(filtered_df["Approved"].sum())
total_pending  = float(filtered_df["Pending"].sum())
total_rejected = float(filtered_df["Rejected"].sum())
total_checked  = float(filtered_df["Total_Checked"].sum())

overall_progress = (total_checked / total_sample * 100) if total_sample > 0 else 0
approval_rate_of_target = (total_approved / total_sample * 100) if total_sample > 0 else 0
rejection_rate_of_checked = (total_rejected / total_checked * 100) if total_checked > 0 else 0

c1, c2, c3, c4 = st.columns(4)

with c1:
    st.markdown(f"""
    <div class="metric-card">
        <div class="kpi-label">{tool_choice} - TOTAL TARGET</div>
        <div class="kpi-value">{total_sample:,.0f}</div>
        <div class="kpi-change neutral">🏙️ {filtered_df["Province"].nunique():,} Provinces | 🏘️ {filtered_df["District"].nunique():,} Districts</div>
    </div>
    """, unsafe_allow_html=True)

with c2:
    st.markdown(f"""
    <div class="metric-card">
        <div class="kpi-label">OVERALL PROGRESS</div>
        <div class="kpi-value">{overall_progress:.1f}%</div>
        <div class="kpi-change positive">✅ {total_checked:,.0f} Checked | ⏳ {max(total_sample-total_checked,0):,.0f} Remaining</div>
    </div>
    """, unsafe_allow_html=True)

with c3:
    st.markdown(f"""
    <div class="metric-card">
        <div class="kpi-label">APPROVAL RATE (OF TARGET)</div>
        <div class="kpi-value">{approval_rate_of_target:.1f}%</div>
        <div class="kpi-change">
            <span class="positive">✓ {total_approved:,.0f} Approved</span> |
            <span class="negative">✗ {total_rejected:,.0f} Rejected</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

with c4:
    st.markdown(f"""
    <div class="metric-card">
        <div class="kpi-label">PENDING + REJECTION RATE</div>
        <div class="kpi-value">{total_pending:,.0f}</div>
        <div class="kpi-change neutral">⚠️ {rejection_rate_of_checked:.1f}% Rejection Rate (of Checked)</div>
    </div>
    """, unsafe_allow_html=True)

# =========================
# Maps (Afghanistan + Province Districts)
# =========================
st.markdown('<div class="section-header">🗺️ Maps</div>', unsafe_allow_html=True)

# Load geojson
try:
    adm1 = load_geojson(ADM1_GEOJSON_URL)
    adm2 = load_geojson(ADM2_GEOJSON_URL)
except Exception as e:
    st.warning("⚠️ نتوانستم GeoJSON نقشه را دانلود کنم. (اگر اینترنت/گیت‌هاب بلاک باشد)")
    st.code(str(e))
    adm1, adm2 = None, None

# Province summary for map (ADM1)
prov_summary = filtered_df.groupby("Province", as_index=False).agg({
    "Total_Sample_Size":"sum",
    "Total_Checked":"sum",
    "Total_Received":"sum",
    "Approved":"sum",
    "Rejected":"sum",
    "Pending":"sum"
})
prov_summary["Progress_Percentage"] = np.where(
    prov_summary["Total_Sample_Size"] > 0,
    (prov_summary["Total_Checked"] / prov_summary["Total_Sample_Size"] * 100),
    0
).round(1)

# District summary for second map (ADM2)
dist_summary = filtered_df.groupby(["Province","District"], as_index=False).agg({
    "Total_Sample_Size":"sum",
    "Total_Checked":"sum",
    "Total_Received":"sum",
    "Approved":"sum",
    "Rejected":"sum",
    "Pending":"sum"
})
dist_summary["Progress_Percentage"] = np.where(
    dist_summary["Total_Sample_Size"] > 0,
    (dist_summary["Total_Checked"] / dist_summary["Total_Sample_Size"] * 100),
    0
).round(1)

map_col1, map_col2 = st.columns(2)

with map_col1:
    st.markdown("##### 🇦🇫 Afghanistan Map (Province Highlight)")
    if adm1 is None:
        st.info("GeoJSON در دسترس نیست.")
    else:
        # geoBoundaries usually uses properties.shapeName
        # We match sheet Province names to geojson shapeName (case-insensitive)
        prov_summary["_prov_key"] = prov_summary["Province"].str.strip().str.lower()

        fig_afg = px.choropleth(
            prov_summary,
            geojson=adm1,
            locations="_prov_key",
            color="Progress_Percentage",
            featureidkey="properties.shapeName",   # geoBoundaries
            hover_name="Province",
            hover_data={
                "Progress_Percentage": True,
                "Total_Sample_Size": True,
                "Total_Checked": True,
                "Approved": True,
                "Rejected": True,
                "Pending": True,
                "_prov_key": False
            },
            title=f"{tool_choice} - Progress by Province"
        )
        fig_afg.update_geos(fitbounds="locations", visible=False)

        # If province filter selected, zoom to that province only (visual focus)
        if selected_province != "All":
            prov_focus = prov_summary[prov_summary["_prov_key"] == selected_province.strip().lower()]
            if not prov_focus.empty:
                fig_afg.update_layout(title=f"{tool_choice} - Selected Province: {selected_province}")

        fig_afg.update_layout(height=520, margin=dict(l=0, r=0, t=40, b=0))
        st.plotly_chart(fig_afg, use_container_width=True)

with map_col2:
    st.markdown("##### 🧭 District Map (within selected Province)")
    if adm2 is None:
        st.info("GeoJSON در دسترس نیست.")
    else:
        # For district map you MUST select a province (otherwise too many districts)
        if selected_province == "All":
            st.info("برای نقشه ولسوالی‌ها، لطفاً یک ولایت را از فلتر انتخاب کن.")
        else:
            ds = dist_summary[dist_summary["Province"] == selected_province].copy()
            if ds.empty:
                st.info("برای این ولایت دیتای ولسوالی موجود نیست.")
            else:
                ds["_dist_key"] = ds["District"].str.strip().str.lower()

                # geoBoundaries ADM2 districts: properties.shapeName is district name
                fig_dist = px.choropleth(
                    ds,
                    geojson=adm2,
                    locations="_dist_key",
                    color="Progress_Percentage",
                    featureidkey="properties.shapeName",
                    hover_name="District",
                    hover_data={
                        "Progress_Percentage": True,
                        "Total_Sample_Size": True,
                        "Total_Checked": True,
                        "Total_Received": True,
                        "Approved": True,
                        "Rejected": True,
                        "Pending": True,
                        "_dist_key": False
                    },
                    title=f"{tool_choice} - District Progress in {selected_province}"
                )
                fig_dist.update_geos(fitbounds="locations", visible=False)
                fig_dist.update_layout(height=520, margin=dict(l=0, r=0, t=40, b=0))
                st.plotly_chart(fig_dist, use_container_width=True)

# =========================
# Charts / Overview
# =========================
st.markdown('<div class="section-header">📊 Data Overview</div>', unsafe_allow_html=True)

tab1, tab2, tab3, tab4 = st.tabs(["Progress Gauge", "Status Analysis", "Regional Performance", "Target vs Checked"])

with tab1:
    fig1 = go.Figure()
    fig1.add_trace(go.Indicator(
        mode="gauge+number",
        value=float(overall_progress),
        title={'text': f"{tool_choice} - Overall Progress"},
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
    fig1.update_layout(height=300, margin=dict(l=40, r=40, t=60, b=20))
    st.plotly_chart(fig1, use_container_width=True)

with tab2:
    cc1, cc2 = st.columns(2)

    with cc1:
        status_data = filtered_df.groupby("Progress_Status").size().reset_index(name="Count")
        if status_data.empty:
            st.info("No data for selected filters.")
        else:
            fig2 = px.pie(status_data, values="Count", names="Progress_Status", hole=0.4,
                         title="Progress Status Distribution")
            st.plotly_chart(fig2, use_container_width=True)

    with cc2:
        review_data = pd.DataFrame({
            "Status": ["Approved", "Pending", "Rejected", "Remaining (Target-Checked)"],
            "Count": [
                total_approved,
                total_pending,
                total_rejected,
                max(total_sample - total_checked, 0)
            ]
        })
        fig3 = px.bar(review_data, x="Status", y="Count", title="Review/Remaining Breakdown")
        fig3.update_layout(xaxis_title="", yaxis_title="Count")
        st.plotly_chart(fig3, use_container_width=True)

with tab3:
    regional_data = filtered_df.groupby("Region", as_index=False).agg({
        "Total_Sample_Size":"sum",
        "Total_Checked":"sum",
        "Approved":"sum",
        "Rejected":"sum",
        "Pending":"sum"
    })
    if regional_data.empty:
        st.info("No data for selected filters.")
    else:
        regional_data["Progress"] = np.where(
            regional_data["Total_Sample_Size"] > 0,
            (regional_data["Total_Checked"] / regional_data["Total_Sample_Size"] * 100),
            0
        ).round(1)

        fig4 = px.bar(
            regional_data.sort_values("Progress", ascending=False),
            x="Region", y="Progress",
            title=f"{tool_choice} - Progress by Region",
            labels={"Progress":"Progress %"}
        )
        st.plotly_chart(fig4, use_container_width=True)
        st.dataframe(regional_data.sort_values("Progress", ascending=False), use_container_width=True, height=260)

with tab4:
    if filtered_df.empty:
        st.info("No data for selected filters.")
    else:
        fig5 = px.scatter(
            filtered_df,
            x="Total_Sample_Size",
            y="Total_Checked",
            color="Progress_Percentage",
            hover_name="District",
            hover_data=["Province","Region","Approved","Rejected","Pending","Total_Received"],
            title=f"{tool_choice} - Target vs Checked",
            labels={"Total_Sample_Size":"Target", "Total_Checked":"Checked"}
        )
        st.plotly_chart(fig5, use_container_width=True)

# =========================
# Detailed Tables
# =========================
st.markdown('<div class="section-header">📋 Detailed Data Analysis</div>', unsafe_allow_html=True)

left, right = st.columns(2)

with left:
    st.markdown("##### 🏙️ Provincial Summary")
    prov_tbl = filtered_df.groupby(["Region","Province"], as_index=False).agg({
        "District":"nunique",
        "Total_Sample_Size":"sum",
        "Total_Received":"sum",
        "Approved":"sum",
        "Pending":"sum",
        "Rejected":"sum",
        "Total_Checked":"sum",
        "Progress_Percentage":"mean"
    }).round(2)
    prov_tbl = prov_tbl.rename(columns={"District":"Districts", "Progress_Percentage":"Avg_Progress"})
    st.dataframe(prov_tbl.sort_values("Avg_Progress", ascending=False), use_container_width=True, height=420)

with right:
    st.markdown("##### 🏘️ District Summary")
    metric_option = st.selectbox(
        "Sort by",
        ["Progress_Percentage","Total_Sample_Size","Total_Checked","Total_Received","Approved","Rejected","Pending"]
    )
    dist_tbl = filtered_df.groupby(["Province","District"], as_index=False).agg({
        "Total_Sample_Size":"sum",
        "Total_Received":"sum",
        "Approved":"sum",
        "Pending":"sum",
        "Rejected":"sum",
        "Total_Checked":"sum",
        "Progress_Percentage":"mean"
    }).round(2)
    st.dataframe(dist_tbl.sort_values(metric_option, ascending=False).head(40), use_container_width=True, height=420)

# =========================
# Alerts
# =========================
st.markdown('<div class="section-header">⚠️ Alerts & Critical Issues</div>', unsafe_allow_html=True)

tmp = filtered_df.copy()
tmp["Rejected_Rate_Checked"] = np.where(tmp["Total_Checked"] > 0, tmp["Rejected"] / tmp["Total_Checked"], 0)
tmp["Received_Rate"] = np.where(tmp["Total_Sample_Size"] > 0, tmp["Total_Received"] / tmp["Total_Sample_Size"], 0)

critical_issues = tmp[
    (tmp["Progress_Percentage"] < 40) |
    (tmp["Rejected_Rate_Checked"] > 0.2) |
    (tmp["Received_Rate"] < 0.5)
].copy()

if not critical_issues.empty:
    critical_issues["Issue_Type"] = critical_issues.apply(
        lambda row:
            "Low Progress" if row["Progress_Percentage"] < 40
            else "High Rejection" if row["Rejected_Rate_Checked"] > 0.2
            else "Low Collection" if row["Received_Rate"] < 0.5
            else "Other",
        axis=1
    )
    st.dataframe(
        critical_issues[["Region","Province","District","Issue_Type","Progress_Percentage",
                        "Total_Sample_Size","Total_Received","Total_Checked","Approved","Rejected","Pending"]]
        .sort_values("Progress_Percentage"),
        use_container_width=True,
        height=320
    )
else:
    st.success("✅ No critical issues detected! All regions are performing well.")

# =========================
# Export
# =========================
st.markdown('<div class="section-header">📤 Export Reports</div>', unsafe_allow_html=True)

e1, e2, e3 = st.columns(3)

with e1:
    if st.button("📋 Download Summary CSV", use_container_width=True):
        summary = filtered_df.describe().round(2)
        st.download_button(
            "⬇️ Download",
            data=summary.to_csv().encode("utf-8"),
            file_name=f"{tool_choice}_summary.csv",
            mime="text/csv",
            use_container_width=True
        )

with e2:
    if st.button("📊 Download Detailed CSV", use_container_width=True):
        st.download_button(
            "⬇️ Download",
            data=filtered_df.to_csv(index=False).encode("utf-8"),
            file_name=f"{tool_choice}_detailed.csv",
            mime="text/csv",
            use_container_width=True
        )

with e3:
    st.info("Custom export columns:")
    selected_cols = st.multiselect(
        "Select columns",
        ["Region","Province","District","Total_Sample_Size","Total_Received","Total_Checked","Approved","Pending","Rejected","Progress_Percentage","Progress_Status"],
        default=["Region","Province","District","Total_Sample_Size","Total_Checked","Approved","Rejected","Progress_Percentage"]
    )
    if selected_cols and st.button("🎯 Download Custom CSV", use_container_width=True):
        out = filtered_df[selected_cols].copy()
        st.download_button(
            "⬇️ Download",
            data=out.to_csv(index=False).encode("utf-8"),
            file_name=f"{tool_choice}_custom.csv",
            mime="text/csv",
            use_container_width=True
        )

# =========================
# Footer + Sidebar info
# =========================
st.markdown("---")
mid = st.columns(3)[1]
with mid:
    st.markdown(f"""
    <div style="text-align: center; color: #6B7280; font-size: 0.9rem;">
        <p>📅 Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}</p>
        <p>🧰 Tool: {tool_choice} | Records: {len(filtered_df):,} | Provinces: {filtered_df["Province"].nunique():,} | Districts: {filtered_df["District"].nunique():,}</p>
        <p>🔍 Filter: Region={selected_region}, Province={selected_province}, District={selected_district}</p>
    </div>
    """, unsafe_allow_html=True)

st.sidebar.markdown("---")
st.sidebar.markdown("### ℹ️ Notes")
st.sidebar.info("""
- فلتر تاریخ حذف شد ✅
- انتخاب Tool اضافه شد (CBE / PBs / Total) ✅
- Region/Province/District از ستون‌های A/B/C شیت خوانده می‌شود ✅
- محاسبات فقط بر اساس لیبل‌های شروع‌شونده با:
  - CBE-  (برای CBE)
  - PBs-  (برای مکاتب عامه)
  - Total- (عمومی)
- ردیف‌های Total حذف می‌شود ✅
- نقشه افغانستان + نقشه ولسوالی‌های ولایت انتخاب‌شده اضافه شد ✅
""")
