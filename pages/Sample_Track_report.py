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

    .dataframe {
        border-radius: 10px;
        overflow: hidden;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05);
    }

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
    .progress-bar {
        height: 10px;
        background-color: #E5E7EB;
        border-radius: 5px;
        overflow: hidden;
        margin: 5px 0;
    }
    .progress-fill {
        height: 100%;
        border-radius: 5px;
    }
</style>
""", unsafe_allow_html=True)

# =========================
# Header
# =========================
st.markdown('<div class="main-header">📊 Sample Track Analytics Dashboard</div>', unsafe_allow_html=True)

# =========================
# ✅ Region → Province → District Mapping (NO TOTAL rows)
# =========================
PROVINCE_HIERARCHY = {
    "Badakhshan": {"region": "North East", "districts": ["Darayem","Jorm","Shahr-e-Buzorg","Teshkan","Warduj"]},
    "Badghis": {"region": "West", "districts": ["Ab Kamari","Jawand","Qadis","Qala-e-Naw"]},
    "Baghlan": {"region": "North East", "districts": ["Baghlan-e-Jadid","Nahrin","Pul-e-Khumri","Tala Wa Barfak"]},
    "Balkh": {"region": "North", "districts": ["Alburz","Balkh","Chahi","Charkent","Kaldar","Khulm","Mazar-e-Sharif","Nahr-e-Shahi"]},
    "Bamyan": {"region": "Central Highland", "districts": ["Kahmard","Sayghan","Shibar","Waras","Yakawlang"]},
    "Daykundi": {"region": "Central Highland", "districts": ["Ashtarlay","Kajran","Khadir","Kiti","Nawmish","Nili","Shahrestan"]},
    "Farah": {"region": "West", "districts": ["Lash-e-Juwayn","Qala-e-Kah","Shibkoh"]},
    "Faryab": {"region": "North", "districts": ["Andkhoy","Bilcheragh","Dawlat Abad","Garzewan","Khan-e-Char Bagh","Khwaja Sabz Posh","Qaysar","Qurghan","Shirin Tagab"]},
    "Ghazni": {"region": "South East", "districts": ["Ab Band","Ajristan","Deh Yak","Gelan","Ghazni","Khwaja Umari","Malistan","Rashidan","Waghaz","Wal-e-Muhammad-e-Shahid","Zanakhan"]},
    "Ghor": {"region": "West", "districts": ["Chaghcharan","Charsadra","Dawlatyar","Feroz Koh","Morghab","Saghar","Taywarah","Tolak"]},
    "Hilmand": {"region": "South", "districts": ["Lashkargah"]},
    "Hirat": {"region": "West", "districts": ["Adraskan","Hirat","Shindand","Zer-i Koh"]},
    "Jawzjan": {"region": "North", "districts": ["Aqcha","Darzab","Fayzabad","Khamyab","Khanaqa","Khwaja Dukoh","Mardyan","Qarqin","Qush Tepa","Shiberghan"]},
    "Kabul": {"region": "Central", "districts": ["Bagrami","Kabul","Khak-e-Jabbar","Musahi","Surobi"]},
    "Kandahar": {"region": "South", "districts": ["Arghandab","Arghestan","Kandahar","Khakrez"]},
    "Kapisa": {"region": "Central", "districts": ["Hisa-e-Awal-e-Kohistan","Hisa-e-Duwum-e-Kohistan","Koh Band","Mahmood-e-Raqi","Tagab"]},
    "Khost": {"region": "South East", "districts": ["Mandozayi","Musa Khel","Nadir Shah Kot","Qalandar","Sabari","Tani","Terezayi"]},
    "Kunar": {"region": "East", "districts": ["Dangam"]},
    "Kunduz": {"region": "North East", "districts": ["Ali Abad","Aqtash","Chahar Darah","Dasht-e-Archi","Qala-e-Zal"]},
    "Laghman": {"region": "East", "districts": ["Badpakh","Dawlatshah","Mehtarlam","Qarghayi"]},
    "Logar": {"region": "Central", "districts": ["Azra"]},
    "Maidan Wardak": {"region": "Central", "districts": ["Chak-e-Wardak","Maydan Shahr","Saydabad"]},
    "Nangarhar": {"region": "East", "districts": ["Deh Bala","Jalalabad","Kama","Khogyani","Rodat"]},
    "Nimroz": {"region": "South", "districts": ["Zaranj"]},
    "Nuristan": {"region": "East", "districts": ["Duab","Kamdesh","Mandol","Wama","Waygal"]},
    "Paktika": {"region": "South East", "districts": ["Dila","Omna","Sar Rawzah","Surobi","Yahya Khel","Yosuf Khel","Zarghun Shahr"]},
    "Paktya": {"region": "South East", "districts": ["Ahmadaba","Chamkani","Dand Wa Patan","Garde Serai","Jaji","Jani Khel","Rohanibaba","Sayed Karam","Zadran","Zurmat"]},
    "Panjsher": {"region": "Central", "districts": ["Anawa","Bazarak"]},
    "Parwan": {"region": "Central", "districts": ["Bagram","Koh-e-Safi","Salang","Shinwari"]},
    "Samangan": {"region": "North", "districts": ["Aybak","Feroz Nakhchir","Hazrat-e-Sultan","Khulm"]},
    "Sar-e-Pul": {"region": "North", "districts": ["Gosfandi","Sayad"]},
    "Takhar": {"region": "North East", "districts": ["Dasht-e-Qala","Farkhar","Kalafgan","Khwaja Ghar","Yangi Qala"]},
    "Uruzgan": {"region": "South", "districts": ["Chora","Khas Uruzgan","Tirinkot"]},
    "Zabul": {"region": "South", "districts": ["Arghandab","Mizan","Nawbahar","Qalat","Tarnak Wa Jaldak"]},
}

# =========================
# Sample Data Loader (respects hierarchy)
# =========================
@st.cache_data
def load_sample_data():
    np.random.seed(42)
    provinces = list(PROVINCE_HIERARCHY.keys())

    rows = []
    for _ in range(200):
        province = np.random.choice(provinces)
        region = PROVINCE_HIERARCHY[province]["region"]
        district = np.random.choice(PROVINCE_HIERARCHY[province]["districts"])

        cbe_sample = np.random.randint(50, 500)
        pb_sample  = np.random.randint(20, 300)

        cbe_received = int(cbe_sample * np.random.uniform(0.6, 1.0))
        pb_received  = int(pb_sample  * np.random.uniform(0.5, 1.0))

        approved = int((cbe_received + pb_received) * np.random.uniform(0.3, 0.8))
        pending  = int((cbe_received + pb_received) * np.random.uniform(0.1, 0.3))
        rejected = int((cbe_received + pb_received) * np.random.uniform(0.05, 0.15))
        not_checked = cbe_received + pb_received - approved - pending - rejected

        total_checked = approved + pending + rejected
        total_sample  = cbe_sample + pb_sample

        progress = int((total_checked / total_sample) * 100) if total_sample > 0 else 0
        remaining = total_sample - total_checked

        rows.append({
            "Region": region,
            "Province": province,
            "District": district,

            "CBE_Sample_Size": cbe_sample,
            "PB_Sample_Size": pb_sample,
            "Total_Sample_Size": total_sample,

            "CBE_Data_Received": cbe_received,
            "PB_Data_Received": pb_received,
            "Total_Received": cbe_received + pb_received,

            "Approved": approved,
            "Pending": pending,
            "Rejected": rejected,
            "Not_Checked": not_checked,

            "Total_Checked": total_checked,
            "Remaining": remaining,
            "Progress_Percentage": min(progress, 100),
            "Progress_Status": "On Track" if progress >= 70 else "Behind Schedule" if progress >= 40 else "Critical",
            "Enumerators": np.random.randint(1, 10),
            "Last_Updated": pd.Timestamp.now() - pd.Timedelta(days=np.random.randint(0, 30))
        })

    return pd.DataFrame(rows)

df = load_sample_data()

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
        <div class="kpi-label">TOTAL SAMPLE SIZE</div>
        <div class="kpi-value">{total_sample:,.0f}</div>
        <div class="kpi-change neutral">📊 {filtered_df["District"].nunique()} Districts</div>
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown(f"""
    <div class="metric-card">
        <div class="kpi-label">OVERALL PROGRESS</div>
        <div class="kpi-value">{overall_progress:.1f}%</div>
        <div class="kpi-change positive">✅ {total_checked:,.0f} Checked | ⏳ {total_sample - total_checked:,.0f} Remaining</div>
    </div>
    """, unsafe_allow_html=True)

with col3:
    st.markdown(f"""
    <div class="metric-card">
        <div class="kpi-label">APPROVAL RATE</div>
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
        <div class="kpi-change neutral">⚠️ {rejection_rate:.1f}% Rejection Rate</div>
    </div>
    """, unsafe_allow_html=True)

# =========================
# Overview Charts
# =========================
st.markdown('<div class="section-header">📊 Data Overview</div>', unsafe_allow_html=True)

tab1, tab2, tab3, tab4 = st.tabs(["Progress Distribution", "Status Analysis", "Regional Performance", "Sample Breakdown"])

with tab1:
    fig1 = go.Figure()
    fig1.add_trace(go.Indicator(
        mode="gauge+number",
        value=overall_progress,
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
            "Count": [total_approved, total_pending, total_rejected, max(total_sample - total_checked, 0)]
        })
        fig3 = px.bar(review_data, x="Status", y="Count", title="Review Status Breakdown")
        fig3.update_layout(xaxis_title="", yaxis_title="Count")
        st.plotly_chart(fig3, use_container_width=True)

with tab3:
    regional_data = filtered_df.groupby("Region").agg({
        "Total_Sample_Size": "sum",
        "Total_Checked": "sum",
        "Approved": "sum",
        "Rejected": "sum"
    }).reset_index()

    if regional_data.empty:
        st.info("No data for selected filters.")
    else:
        regional_data["Progress"] = np.where(
            regional_data["Total_Sample_Size"] > 0,
            (regional_data["Total_Checked"] / regional_data["Total_Sample_Size"] * 100).round(1),
            0
        )
        regional_data["Approval_Rate"] = np.where(
            regional_data["Total_Checked"] > 0,
            (regional_data["Approved"] / regional_data["Total_Checked"] * 100).round(1),
            0
        )

        fig4 = px.bar(
            regional_data.sort_values("Progress", ascending=False),
            x="Region",
            y=["Progress", "Approval_Rate"],
            barmode="group",
            title="Regional Performance Comparison",
            labels={"value": "Percentage", "variable": "Metric"}
        )
        st.plotly_chart(fig4, use_container_width=True)

with tab4:
    sample_data = filtered_df.groupby("Province").agg({
        "CBE_Sample_Size": "sum",
        "PB_Sample_Size": "sum",
        "Total_Checked": "sum"
    }).reset_index()

    if sample_data.empty:
        st.info("No data for selected filters.")
    else:
        denom = sample_data["CBE_Sample_Size"] + sample_data["PB_Sample_Size"]
        sample_data["Check_Rate"] = np.where(denom > 0, (sample_data["Total_Checked"] / denom * 100).round(1), 0)

        fig5 = px.scatter(
            sample_data,
            x="CBE_Sample_Size",
            y="PB_Sample_Size",
            size="Total_Checked",
            color="Check_Rate",
            hover_name="Province",
            title="Sample Size vs Check Progress by Province",
            labels={
                "CBE_Sample_Size": "CBE Sample Size",
                "PB_Sample_Size": "PB Sample Size",
                "Total_Checked": "Total Checked",
                "Check_Rate": "Check Rate (%)"
            }
        )
        st.plotly_chart(fig5, use_container_width=True)

# =========================
# Detailed Data Analysis
# =========================
st.markdown('<div class="section-header">📋 Detailed Data Analysis</div>', unsafe_allow_html=True)

c1, c2 = st.columns(2)

with c1:
    st.markdown("##### 🏙️ Provincial Summary")
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
            "Total_Sample_Size": "Sample_Size",
            "Total_Received": "Received",
            "Total_Checked": "Checked"
        })

        provincial_summary["Status"] = provincial_summary["Avg_Progress"].apply(
            lambda x: "🟢 On Track" if x >= 70 else "🟡 Behind" if x >= 40 else "🔴 Critical"
        )

        st.dataframe(
            provincial_summary.sort_values("Avg_Progress", ascending=False),
            use_container_width=True,
            height=400
        )

with c2:
    st.markdown("##### 📊 Performance Metrics by District")

    metric_option = st.selectbox(
        "Select Metric for District Ranking",
        ["Progress_Percentage", "Approved", "Rejected", "Pending", "Total_Checked"]
    )

    district_summary = filtered_df.groupby(["Province", "District"]).agg({
        "Total_Sample_Size": "sum",
        "Total_Received": "sum",
        "Approved": "sum",
        "Pending": "sum",
        "Rejected": "sum",
        "Total_Checked": "sum",
        "Progress_Percentage": "mean",
        "Enumerators": "max"
    }).round(2).reset_index()

    if district_summary.empty:
        st.info("No data for selected filters.")
    else:
        district_summary = district_summary.sort_values(metric_option, ascending=False).head(20)

        display_df = district_summary.copy()
        display_df["Progress_Bar"] = display_df["Progress_Percentage"].apply(
            lambda x: (
                f"<div class='progress-bar'>"
                f"<div class='progress-fill' style='width:{min(x,100)}%; "
                f"background-color:{'#10B981' if x>=70 else '#F59E0B' if x>=40 else '#EF4444'}'></div></div>"
            )
        )

        st.dataframe(
            display_df[["Province","District","Total_Sample_Size","Approved","Pending","Rejected","Progress_Percentage","Progress_Bar"]],
            use_container_width=True,
            height=400
        )

# =========================
# Target Achievement Analysis
# =========================
st.markdown('<div class="section-header">🎯 Target Achievement Analysis</div>', unsafe_allow_html=True)

target_analysis = filtered_df.copy()
target_analysis["Achievement_Rate"] = np.where(
    target_analysis["Total_Sample_Size"] > 0,
    (target_analysis["Total_Checked"] / target_analysis["Total_Sample_Size"] * 100).round(1),
    0
)
target_analysis["Approval_Rate"] = np.where(
    target_analysis["Total_Checked"] > 0,
    (target_analysis["Approved"] / target_analysis["Total_Checked"] * 100).round(1),
    0
)
target_analysis["Rejection_Rate"] = np.where(
    target_analysis["Total_Checked"] > 0,
    (target_analysis["Rejected"] / target_analysis["Total_Checked"] * 100).round(1),
    0
)

fig6 = go.Figure()

if not target_analysis.empty:
    fig6.add_trace(go.Scatter(
        x=target_analysis["Total_Sample_Size"],
        y=target_analysis["Total_Checked"],
        mode="markers",
        marker=dict(
            size=np.maximum(target_analysis["Progress_Percentage"] / 5, 6),
            color=target_analysis["Progress_Percentage"],
            colorscale="RdYlGn",
            showscale=True,
            colorbar=dict(title="Progress %")
        ),
        text=target_analysis["District"],
        hovertemplate=(
            "<b>%{text}</b><br><br>"
            "Sample Size: %{x}<br>"
            "Checked: %{y}<br>"
            "Progress: %{marker.color}%<br>"
            "<extra></extra>"
        ),
        name="Districts"
    ))

    max_val = max(target_analysis["Total_Sample_Size"].max(), target_analysis["Total_Checked"].max())
    fig6.add_trace(go.Scatter(
        x=[0, max_val],
        y=[0, max_val],
        mode="lines",
        line=dict(color="gray", dash="dash"),
        name="Target Line"
    ))

fig6.update_layout(
    title="Sample Size vs Checked Progress",
    xaxis_title="Sample Size (Target)",
    yaxis_title="Checked (Achievement)",
    hovermode="closest",
    height=500
)

st.plotly_chart(fig6, use_container_width=True)

# =========================
# Alerts (✅ safe division)
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

    alert_cols = st.columns(4)
    alert_metrics = {
        "Critical Districts": critical_issues["District"].nunique(),
        "Low Progress (<40%)": int((critical_issues["Progress_Percentage"] < 40).sum()),
        "High Rejection (>20%)": int((critical_issues["Rejected_Rate_Checked"] > 0.2).sum()),
        "Low Collection (<50%)": int((critical_issues["Received_Rate"] < 0.5).sum())
    }

    for col, (label, value) in zip(alert_cols, alert_metrics.items()):
        with col:
            st.metric(label=label, value=value)

    st.dataframe(
        critical_issues[["Region","Province","District","Issue_Type","Progress_Percentage",
                         "Total_Sample_Size","Total_Received","Approved","Rejected"]].sort_values("Progress_Percentage"),
        use_container_width=True,
        height=300
    )
else:
    st.success("✅ No critical issues detected! All regions are performing well.")

# =========================
# Export Reports
# =========================
st.markdown('<div class="section-header">📤 Export Reports</div>', unsafe_allow_html=True)

e1, e2, e3 = st.columns(3)

with e1:
    if st.button("📋 Generate Summary Report", use_container_width=True):
        summary_report = filtered_df.describe().round(2)
        st.download_button(
            label="📥 Download Summary CSV",
            data=summary_report.to_csv().encode("utf-8"),
            file_name="sample_track_summary.csv",
            mime="text/csv",
            use_container_width=True
        )

with e2:
    if st.button("📊 Generate Detailed Report", use_container_width=True):
        detailed_report = filtered_df.copy()
        st.download_button(
            label="📥 Download Full Data CSV",
            data=detailed_report.to_csv(index=False).encode("utf-8"),
            file_name="sample_track_detailed.csv",
            mime="text/csv",
            use_container_width=True
        )

with e3:
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
footer_cols = st.columns(3)
with footer_cols[1]:
    st.markdown(f"""
    <div style="text-align: center; color: #6B7280; font-size: 0.9rem;">
        <p>📅 Last Updated: {datetime.now().strftime('%Y-%m-%d %H:%M')}</p>
        <p>📊 Total Records: {len(filtered_df):,} | Districts: {filtered_df["District"].nunique():,}</p>
        <p>🔍 Filter Applied: Region={selected_region}, Province={selected_province}, District={selected_district}</p>
    </div>
    """, unsafe_allow_html=True)

# =========================
# Sidebar Info + Settings
# =========================
st.sidebar.markdown("---")
st.sidebar.markdown("### ℹ️ About This Dashboard")
st.sidebar.info("""
This dashboard provides comprehensive tracking and analysis of sample collection progress across all regions.

**Key Features:**
- Real-time progress monitoring
- Detailed status analysis
- Target achievement tracking
- Critical issue alerts
- Export capabilities
""")

st.sidebar.markdown("### ⚙️ Settings")
auto_refresh = st.sidebar.checkbox("Auto-refresh data", value=False)
if auto_refresh:
    refresh_rate = st.sidebar.slider("Refresh rate (seconds)", 30, 300, 60)
    st.sidebar.caption(f"Next refresh in {refresh_rate} seconds")
    st.rerun()

# =========================
# Note: Google Sheets integration example (optional)
# =========================
"""
@st.cache_data(ttl=300)
def load_actual_data():
    import gspread
    from google.oauth2.service_account import Credentials

    scopes = ["https://www.googleapis.com/auth/spreadsheets.readonly"]
    creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scopes)

    client = gspread.authorize(creds)
    spreadsheet = client.open_by_key("YOUR_SPREADSHEET_KEY")
    worksheet = spreadsheet.worksheet("Sample_Track")

    data = worksheet.get_all_records()
    df = pd.DataFrame(data)

    # ✅ Optional: force correct Region/District based on mapping
    # df["Region"] = df["Province"].map(lambda p: PROVINCE_HIERARCHY.get(p, {}).get("region", df.get("Region")))
    # ... more cleaning ...

    return df
"""
