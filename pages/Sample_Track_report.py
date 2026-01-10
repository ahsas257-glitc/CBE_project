import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
import plotly.graph_objects as go
import plotly.express as px

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
    .metric-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 8px 12px rgba(0, 0, 0, 0.1);
    }
    .kpi-label {
        font-size: 0.9rem;
        font-weight: 500;
        color: #475569;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    .kpi-value {
        font-size: 2.2rem;
        font-weight: 700;
        color: #1E3A8A;
        margin: 0.5rem 0;
    }
    .kpi-change {
        font-size: 0.85rem;
        font-weight: 500;
    }
    .positive { color: #059669; }
    .negative { color: #DC2626; }
    .neutral  { color: #6B7280; }

    .stTabs [data-baseweb="tab-list"] { gap: 8px; }
    .stTabs [data-baseweb="tab"] {
        border-radius: 8px 8px 0 0;
        padding: 10px 20px;
        background-color: #F3F4F6;
    }
    .stTabs [aria-selected="true"] {
        background-color: #3B82F6 !important;
        color: white !important;
    }
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-header">📊 Sample Track Analytics Dashboard</div>', unsafe_allow_html=True)

# =========================
# Google Sheets Config
# =========================
SPREADSHEET_KEY = "1lkztBZ4eG1BQx-52XgnA6w8YIiw-Sm85pTlQQziurfw"
WORKSHEET_NAME = "Test"

# =========================
# Column Resolver (based on header labels)
# =========================
SYNONYMS = {
    "Region": ["Region", "region", "REGION", "Zone", "zone", "Zoon", "ریجن", "زون"],
    "Province": ["Province", "province", "PROVINCE", "Prov", "ولایت", "ولسوالى؟", "ولایت/استان"],
    "District": ["District", "district", "DISTRICT", "Disrtict", "Disrtict ", "Dist", "ولسوالی", "ناحیه"],

    # Targets / Sample
    "CBE_Sample_Size": ["CBE_Sample_Size", "CBE Sample Size", "CBE_Target", "CBE Target", "CBE", "Target_CBE"],
    "PB_Sample_Size": ["PB_Sample_Size", "PB Sample Size", "PB_Target", "PB Target", "PB", "Target_PB"],
    "Total_Sample_Size": ["Total_Sample_Size", "Total Sample Size", "Total_Target", "Total Target", "Target", "Sample Size", "Total"],

    # Received / Checked
    "CBE_Data_Received": ["CBE_Data_Received", "CBE Data Received", "CBE_Received", "Received_CBE"],
    "PB_Data_Received": ["PB_Data_Received", "PB Data Received", "PB_Received", "Received_PB"],
    "Total_Received": ["Total_Received", "Total Received", "Received", "TotalReceived"],

    "Approved": ["Approved", "approved", "APPROVED", "Approve", "Appr", "تایید", "تایید شده"],
    "Pending": ["Pending", "pending", "PENDING", "In Review", "Under Review", "در جریان", "منتظر"],
    "Rejected": ["Rejected", "rejected", "REJECTED", "Reject", "رد", "رد شده"],
    "Total_Checked": ["Total_Checked", "Total Checked", "Checked", "Reviewed", "TotalReviewed"],
    "Progress_Percentage": ["Progress_Percentage", "Progress %", "Progress", "Completion %", "Percent", "فیصد"],
    "Enumerators": ["Enumerators", "Enumerator", "No. Enumerators", "Data Collectors", "شمار شمارنده"],

    "Last_Updated": ["Last_Updated", "Last Updated", "Update Date", "Updated", "Date", "تاریخ"]
}

def normalize_colname(x: str) -> str:
    return str(x).strip()

def pick_column(df: pd.DataFrame, canonical: str):
    cols = [normalize_colname(c) for c in df.columns]
    for cand in SYNONYMS.get(canonical, []):
        cand_norm = normalize_colname(cand)
        if cand_norm in cols:
            return cand_norm
    # fallback: contains match
    for c in cols:
        for cand in SYNONYMS.get(canonical, []):
            if normalize_colname(cand).lower() in c.lower():
                return c
    return None

def rename_with_resolver(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    df = df.copy()
    df.columns = [normalize_colname(c) for c in df.columns]

    mapping = {}
    for canonical in SYNONYMS.keys():
        found = pick_column(df, canonical)
        if found and found != canonical:
            mapping[found] = canonical

    df = df.rename(columns=mapping)
    return df, mapping

def remove_total_rows(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    for col in ["Province", "District", "Region"]:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip()
            df = df[~df[col].str.contains(r"\btotal\b", case=False, na=False)]
    return df

def ensure_last_updated(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    if "Last_Updated" in df.columns:
        df["Last_Updated"] = pd.to_datetime(df["Last_Updated"], errors="coerce")
        df["Last_Updated"] = df["Last_Updated"].fillna(pd.Timestamp.now())
    else:
        df["Last_Updated"] = pd.Timestamp.now()
    return df

def to_numeric(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    df = df.copy()
    for c in cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)
    return df

def compute_fields_from_labels(df: pd.DataFrame) -> pd.DataFrame:
    """
    همه محاسبات را بر اساس ستون‌هایی که در شیت موجود است انجام می‌دهد.
    اگر چیزی نبود، از ترکیب سایر ستون‌ها می‌سازد.
    """
    df = df.copy()

    required_text = ["Region", "Province", "District"]
    for c in required_text:
        if c not in df.columns:
            df[c] = "Unknown"
        df[c] = df[c].astype(str).str.strip()

    numeric_candidates = [
        "CBE_Sample_Size","PB_Sample_Size","Total_Sample_Size",
        "CBE_Data_Received","PB_Data_Received","Total_Received",
        "Approved","Pending","Rejected","Total_Checked",
        "Progress_Percentage","Enumerators"
    ]
    for c in numeric_candidates:
        if c not in df.columns:
            df[c] = 0

    df = to_numeric(df, numeric_candidates)

    # Total sample
    if (df["Total_Sample_Size"] == 0).all():
        df["Total_Sample_Size"] = df["CBE_Sample_Size"] + df["PB_Sample_Size"]

    # Total received
    if (df["Total_Received"] == 0).all():
        df["Total_Received"] = df["CBE_Data_Received"] + df["PB_Data_Received"]

    # Total checked
    if (df["Total_Checked"] == 0).all():
        df["Total_Checked"] = df["Approved"] + df["Pending"] + df["Rejected"]

    # Not_Checked (اگر در شیت نبود، بساز)
    if "Not_Checked" not in df.columns:
        df["Not_Checked"] = np.maximum(df["Total_Received"] - (df["Approved"] + df["Pending"] + df["Rejected"]), 0)
    else:
        df["Not_Checked"] = pd.to_numeric(df["Not_Checked"], errors="coerce").fillna(0)

    # Remaining
    if "Remaining" not in df.columns:
        df["Remaining"] = np.maximum(df["Total_Sample_Size"] - df["Total_Checked"], 0)
    else:
        df["Remaining"] = pd.to_numeric(df["Remaining"], errors="coerce").fillna(0)

    # Progress
    if (df["Progress_Percentage"] == 0).all():
        df["Progress_Percentage"] = np.where(
            df["Total_Sample_Size"] > 0,
            (df["Total_Checked"] / df["Total_Sample_Size"] * 100),
            0
        )
    df["Progress_Percentage"] = pd.to_numeric(df["Progress_Percentage"], errors="coerce").fillna(0).clip(0, 100).round(1)

    # Progress Status
    if "Progress_Status" not in df.columns:
        df["Progress_Status"] = df["Progress_Percentage"].apply(
            lambda x: "On Track" if x >= 70 else "Behind Schedule" if x >= 40 else "Critical"
        )
    else:
        df["Progress_Status"] = df["Progress_Status"].astype(str)

    # Enumerators default
    if (df["Enumerators"] == 0).all():
        df["Enumerators"] = 1

    return df

# =========================
# Load from Google Sheet
# =========================
@st.cache_data(ttl=300)
def load_actual_data():
    import gspread
    from google.oauth2.service_account import Credentials

    scopes = ["https://www.googleapis.com/auth/spreadsheets.readonly"]
    creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scopes)
    client = gspread.authorize(creds)

    sh = client.open_by_key(SPREADSHEET_KEY)
    ws = sh.worksheet(WORKSHEET_NAME)
    data = ws.get_all_records()

    df = pd.DataFrame(data)
    df.columns = [normalize_colname(c) for c in df.columns]

    df, rename_map = rename_with_resolver(df)

    df = remove_total_rows(df)
    df = ensure_last_updated(df)
    df = compute_fields_from_labels(df)

    return df, rename_map

# =========================
# Sidebar Data Source
# =========================
st.sidebar.markdown("## 🧩 Data Source")
st.sidebar.caption("Google Sheet → Test")

try:
    df, used_renames = load_actual_data()
except Exception as e:
    st.error("❌ اتصال به Google Sheet موفق نشد. این موارد را چک کن:")
    st.markdown("""
- در Streamlit Cloud → Settings → Secrets باید کل JSON سرویس اکانت را زیر کلید **gcp_service_account** گذاشته باشی
- شیت را با ایمیل Service Account شریک (Share) ساخته باشی (Viewer یا Editor)
- نام ورک‌شیت دقیقاً **Test** باشد
""")
    st.code(str(e))
    st.stop()

# =========================
# Show Header Analysis (labels)
# =========================
with st.expander("🔎 تحلیل لیبل‌های شیت (ستون‌های تشخیص داده شده)", expanded=False):
    st.write("ستون‌های موجود در شیت:")
    st.code(", ".join(df.columns.tolist()))
    st.write("ستون‌هایی که سیستم rename/تشخیص داده:")
    if used_renames:
        st.json(used_renames)
    else:
        st.info("هیچ rename لازم نبود (لیبل‌ها استاندارد بوده).")

# =========================
# Sidebar Filters
# =========================
st.sidebar.markdown("## 🎯 Filters")

st.sidebar.markdown("### 📅 Time Range")
date_range = st.sidebar.date_input(
    "Select Date Range",
    value=(df["Last_Updated"].min().date(), df["Last_Updated"].max().date()),
    min_value=df["Last_Updated"].min().date(),
    max_value=df["Last_Updated"].max().date()
)

st.sidebar.markdown("### 🌍 Region Filter")
all_regions = ["All"] + sorted(df["Region"].unique().tolist())
selected_region = st.sidebar.selectbox("Select Region", all_regions)

st.sidebar.markdown("### 🏙️ Province Filter")
if selected_region != "All":
    province_options = ["All"] + sorted(df[df["Region"] == selected_region]["Province"].unique().tolist())
else:
    province_options = ["All"] + sorted(df["Province"].unique().tolist())
selected_province = st.sidebar.selectbox("Select Province", province_options)

st.sidebar.markdown("### 🏘️ District Filter")
if selected_province != "All":
    district_options = ["All"] + sorted(df[df["Province"] == selected_province]["District"].unique().tolist())
elif selected_region != "All":
    district_options = ["All"] + sorted(df[df["Region"] == selected_region]["District"].unique().tolist())
else:
    district_options = ["All"] + sorted(df["District"].unique().tolist())
selected_district = st.sidebar.selectbox("Select District", district_options)

st.sidebar.markdown("### 📈 Progress Status")
progress_status = st.sidebar.multiselect(
    "Select Progress Status",
    options=["All", "On Track", "Behind Schedule", "Critical"],
    default=["All"]
)

# =========================
# Apply Filters
# =========================
filtered_df = df.copy()

if len(date_range) == 2:
    filtered_df = filtered_df[
        (filtered_df["Last_Updated"].dt.date >= date_range[0]) &
        (filtered_df["Last_Updated"].dt.date <= date_range[1])
    ]

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

total_sample   = filtered_df["Total_Sample_Size"].sum()
total_received = filtered_df["Total_Received"].sum()
total_approved = filtered_df["Approved"].sum()
total_pending  = filtered_df["Pending"].sum()
total_rejected = filtered_df["Rejected"].sum()
total_checked  = filtered_df["Total_Checked"].sum()

overall_progress = (total_checked / total_sample * 100) if total_sample > 0 else 0
completion_rate  = (total_approved / total_sample * 100) if total_sample > 0 else 0
rejection_rate   = (total_rejected / total_checked * 100) if total_checked > 0 else 0

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.markdown(f"""
    <div class="metric-card">
        <div class="kpi-label">TOTAL SAMPLE SIZE (TARGET)</div>
        <div class="kpi-value">{total_sample:,.0f}</div>
        <div class="kpi-change neutral">📍 {filtered_df["Province"].nunique():,} Provinces | 🏘️ {filtered_df["District"].nunique():,} Districts</div>
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown(f"""
    <div class="metric-card">
        <div class="kpi-label">OVERALL PROGRESS</div>
        <div class="kpi-value">{overall_progress:.1f}%</div>
        <div class="kpi-change positive">✅ {total_checked:,.0f} Checked | ⏳ {max(total_sample - total_checked, 0):,.0f} Remaining</div>
    </div>
    """, unsafe_allow_html=True)

with col3:
    st.markdown(f"""
    <div class="metric-card">
        <div class="kpi-label">APPROVAL RATE (of Target)</div>
        <div class="kpi-value">{completion_rate:.1f}%</div>
        <div class="kpi-change">
            <span class="positive">✓ {total_approved:,.0f} Approved</span> |
            <span class="negative">✗ {total_rejected:,.0f} Rejected</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

with col4:
    st.markdown(f"""
    <div class="metric-card">
        <div class="kpi-label">PENDING REVIEW</div>
        <div class="kpi-value">{total_pending:,.0f}</div>
        <div class="kpi-change neutral">⚠️ {rejection_rate:.1f}% Rejection Rate (of Checked)</div>
    </div>
    """, unsafe_allow_html=True)

# =========================
# Overview Charts
# =========================
st.markdown('<div class="section-header">📊 Data Overview</div>', unsafe_allow_html=True)

tab1, tab2, tab3, tab4 = st.tabs(["Progress Gauge", "Status Analysis", "Regional Performance", "Target vs Checked"])

with tab1:
    fig1 = go.Figure()
    fig1.add_trace(go.Indicator(
        mode="gauge+number",
        value=float(overall_progress),
        title={'text': "Overall Progress"},
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
    fig1.update_layout(height=300, margin=dict(l=50, r=50, t=50, b=50))
    st.plotly_chart(fig1, use_container_width=True)

with tab2:
    c1, c2 = st.columns(2)
    with c1:
        status_data = filtered_df.groupby("Progress_Status").size().reset_index(name="Count")
        if status_data.empty:
            st.info("No data for selected filters.")
        else:
            fig2 = px.pie(status_data, values="Count", names="Progress_Status", hole=0.4,
                         title="Progress Status Distribution")
            st.plotly_chart(fig2, use_container_width=True)

    with c2:
        review_data = pd.DataFrame({
            "Status": ["Approved", "Pending", "Rejected", "Not Checked"],
            "Count": [
                total_approved,
                total_pending,
                total_rejected,
                max(total_sample - total_checked, 0)
            ]
        })
        fig3 = px.bar(review_data, x="Status", y="Count", title="Review Status Breakdown")
        fig3.update_layout(xaxis_title="", yaxis_title="Count")
        st.plotly_chart(fig3, use_container_width=True)

with tab3:
    regional_data = filtered_df.groupby("Region").agg({
        "Total_Sample_Size": "sum",
        "Total_Checked": "sum",
        "Approved": "sum",
        "Rejected": "sum",
        "Pending": "sum"
    }).reset_index()

    if regional_data.empty:
        st.info("No data for selected filters.")
    else:
        regional_data["Progress"] = np.where(
            regional_data["Total_Sample_Size"] > 0,
            (regional_data["Total_Checked"] / regional_data["Total_Sample_Size"] * 100).round(1),
            0
        )
        fig4 = px.bar(
            regional_data.sort_values("Progress", ascending=False),
            x="Region",
            y="Progress",
            title="Regional Progress (Checked vs Target)",
            labels={"Progress": "Progress %"}
        )
        st.plotly_chart(fig4, use_container_width=True)
        st.dataframe(regional_data.sort_values("Progress", ascending=False), use_container_width=True, height=280)

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
            hover_data=["Province", "Region", "Approved", "Rejected", "Pending"],
            title="Target (Total Sample) vs Checked by District",
            labels={"Total_Sample_Size": "Target", "Total_Checked": "Checked"}
        )
        st.plotly_chart(fig5, use_container_width=True)

# =========================
# Detailed Tables
# =========================
st.markdown('<div class="section-header">📋 Detailed Data Analysis</div>', unsafe_allow_html=True)

left, right = st.columns(2)

with left:
    st.markdown("##### 🏙️ Provincial Summary (based on sheet labels)")
    provincial_summary = filtered_df.groupby(["Region", "Province"]).agg({
        "District": "nunique",
        "Total_Sample_Size": "sum",
        "Total_Received": "sum",
        "Approved": "sum",
        "Pending": "sum",
        "Rejected": "sum",
        "Total_Checked": "sum",
        "Progress_Percentage": "mean",
        "Enumerators": "sum"
    }).round(2).reset_index()

    if provincial_summary.empty:
        st.info("No data for selected filters.")
    else:
        provincial_summary = provincial_summary.rename(columns={
            "District": "Districts",
            "Progress_Percentage": "Avg_Progress",
            "Total_Sample_Size": "Target_Total",
            "Total_Received": "Received_Total",
            "Total_Checked": "Checked_Total"
        })
        st.dataframe(provincial_summary.sort_values("Avg_Progress", ascending=False), use_container_width=True, height=420)

with right:
    st.markdown("##### 🏘️ District Ranking")
    metric_option = st.selectbox(
        "Select Metric for District Ranking",
        ["Progress_Percentage", "Approved", "Rejected", "Pending", "Total_Checked", "Total_Sample_Size"]
    )

    district_summary = filtered_df.groupby(["Region", "Province", "District"]).agg({
        "Total_Sample_Size": "sum",
        "Total_Received": "sum",
        "Approved": "sum",
        "Pending": "sum",
        "Rejected": "sum",
        "Total_Checked": "sum",
        "Progress_Percentage": "mean"
    }).round(2).reset_index()

    if district_summary.empty:
        st.info("No data for selected filters.")
    else:
        st.dataframe(
            district_summary.sort_values(metric_option, ascending=False).head(30),
            use_container_width=True,
            height=420
        )

# =========================
# Alerts (safe division)
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
                        "Total_Sample_Size","Total_Received","Approved","Rejected","Pending"]]
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
a, b, c = st.columns(3)

with a:
    if st.button("📋 Generate Summary Report", use_container_width=True):
        summary_report = filtered_df.describe().round(2)
        st.download_button(
            label="📥 Download Summary CSV",
            data=summary_report.to_csv().encode("utf-8"),
            file_name="sample_track_summary.csv",
            mime="text/csv",
            use_container_width=True
        )

with b:
    if st.button("📊 Generate Detailed Report", use_container_width=True):
        st.download_button(
            label="📥 Download Full Data CSV",
            data=filtered_df.to_csv(index=False).encode("utf-8"),
            file_name="sample_track_detailed.csv",
            mime="text/csv",
            use_container_width=True
        )

with c:
    st.info("Select metrics for custom report:")
    selected_metrics = st.multiselect(
        "Choose metrics",
        ["Approved","Rejected","Pending","Total_Checked","Progress_Percentage","Total_Sample_Size","Total_Received"],
        default=["Approved","Progress_Percentage"]
    )
    if selected_metrics and st.button("🎯 Generate Custom Report", use_container_width=True):
        custom_report = filtered_df[["Region","Province","District"] + selected_metrics]
        st.download_button(
            label="📥 Download Custom Report",
            data=custom_report.to_csv(index=False).encode("utf-8"),
            file_name="sample_track_custom.csv",
            mime="text/csv",
            use_container_width=True
        )

# =========================
# Footer
# =========================
st.markdown("---")
mid = st.columns(3)[1]
with mid:
    st.markdown(f"""
    <div style="text-align: center; color: #6B7280; font-size: 0.9rem;">
        <p>📅 Last Updated: {datetime.now().strftime('%Y-%m-%d %H:%M')}</p>
        <p>📊 Total Records: {len(filtered_df):,} | Provinces: {filtered_df["Province"].nunique():,} | Districts: {filtered_df["District"].nunique():,}</p>
        <p>🔍 Filter Applied: Region={selected_region}, Province={selected_province}, District={selected_district}</p>
    </div>
    """, unsafe_allow_html=True)

# =========================
# Sidebar Info + Settings
# =========================
st.sidebar.markdown("---")
st.sidebar.markdown("### ℹ️ About")
st.sidebar.info("""
این داشبورد تمام محاسبات را بر اساس لیبل‌های موجود در شیت Test انجام می‌دهد.
- تشخیص هوشمند نام ستون‌ها (مثل Disrtict)
- حذف خودکار ردیف‌های Total
- محاسبه مجموع‌ها بر اساس Target/Approved/Rejected/Pending
""")

st.sidebar.markdown("### ⚙️ Settings")
auto_refresh = st.sidebar.checkbox("Auto-refresh data", value=False)
if auto_refresh:
    refresh_rate = st.sidebar.slider("Refresh rate (seconds)", 30, 300, 60)
    st.sidebar.caption(f"Next refresh in {refresh_rate} seconds")
    st.rerun()
