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
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, 
    PageBreak, Image, ListFlowable, ListItem
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus.flowables import Flowable

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
        font-weight: 800;
        color: #1E3A8A;
        margin-bottom: 1.5rem;
        text-align: center;
        padding: 1.5rem;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border-radius: 16px;
        box-shadow: 0 8px 32px rgba(31, 38, 135, 0.37);
        animation: fadeIn 1s ease-in;
    }
    .section-header {
        font-size: 1.8rem;
        font-weight: 700;
        color: #1E40AF;
        margin-top: 1.5rem;
        margin-bottom: 1rem;
        padding-bottom: 0.5rem;
        border-bottom: 4px solid linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        background: linear-gradient(90deg, #f8fafc 0%, #e2e8f0 100%);
        padding: 12px 20px;
        border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05);
    }
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1.5rem;
        border-radius: 20px;
        color: white;
        box-shadow: 0 10px 25px rgba(0, 0, 0, 0.1);
        transition: transform 0.3s ease;
        height: 160px;
        display: flex;
        flex-direction: column;
        justify-content: center;
    }
    .metric-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 15px 30px rgba(0, 0, 0, 0.15);
    }
    .kpi-label {
        font-size: 0.9rem;
        font-weight: 600;
        color: rgba(255, 255, 255, 0.9);
        letter-spacing: 0.5px;
        text-transform: uppercase;
        margin-bottom: 5px;
    }
    .kpi-value {
        font-size: 2.5rem;
        font-weight: 800;
        color: white;
        margin: 0.5rem 0;
        text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.2);
    }
    .kpi-change {
        font-size: 0.85rem;
        font-weight: 600;
        color: rgba(255, 255, 255, 0.85);
        background: rgba(255, 255, 255, 0.1);
        padding: 4px 10px;
        border-radius: 12px;
        display: inline-block;
    }
    .hint {
        color: #64748B;
        font-size: 0.9rem;
        background: #f8fafc;
        padding: 12px;
        border-radius: 8px;
        border-left: 4px solid #667eea;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        border-radius: 10px 10px 0 0;
        padding: 0 24px;
        font-weight: 600;
        background: #f1f5f9;
        border: none;
    }
    .stTabs [aria-selected="true"] {
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%) !important;
        color: white !important;
    }
    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(-20px); }
        to { opacity: 1; transform: translateY(0); }
    }
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-header">📊 Sample Track Analytics Dashboard</div>', unsafe_allow_html=True)

# =========================
# Google Sheet Config
# =========================
SPREADSHEET_KEY = "1lkztBZ4eG1BQx-52XgnA6w8YIiw-Sm85pTlQQziurfw"
WORKSHEET_NAME = "Test"

# =========================
# GeoJSON sources (Updated)
# =========================
ADM1_GEOJSON_URL = "https://raw.githubusercontent.com/awmc/afghanistan-geojson/master/afg_adm1.geojson"
ADM2_GEOJSON_URL = "https://raw.githubusercontent.com/awmc/afghanistan-geojson/master/afg_adm2.geojson"

# =========================
# Helper Functions
# =========================
def norm_text(x: str) -> str:
    """Normalize names for matching."""
    s = str(x).strip().lower()
    s = s.replace("_", " ").replace("'", "").replace("`", "")
    s = s.replace("  ", " ")
    s = s.replace("sar e pul", "sar-e-pul")
    s = s.replace("sare pul", "sar-e-pul")
    s = s.replace("maidan wardak", "wardak")
    s = s.replace("maydan wardak", "wardak")
    s = s.replace("kunarha", "kunar")
    s = s.replace("nangarharha", "nangarhar")
    s = s.replace("logarha", "logar")
    s = s.replace("paktiaha", "paktia")
    s = s.replace("paktikaha", "paktika")
    s = s.replace("ghazniha", "ghazni")
    s = s.replace("khostha", "khost")
    return s

def remove_total_rows(df: pd.DataFrame) -> pd.DataFrame:
    """Remove rows containing 'total'."""
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

def detect_comment_columns(df: pd.DataFrame) -> list:
    cols = []
    for c in df.columns:
        cl = str(c).strip().lower()
        if "comment" in cl or "remark" in cl or "note" in cl:
            cols.append(c)
    return cols

def summarize_comments(df_raw: pd.DataFrame) -> dict:
    comment_cols = detect_comment_columns(df_raw)
    if not comment_cols:
        return {"comment_cols": [], "non_empty": 0, "top": []}

    tmp = df_raw[comment_cols].copy()
    tmp = tmp.applymap(lambda x: "" if pd.isna(x) else str(x).strip())
    non_empty = int((tmp != "").sum().sum())

    all_comments = []
    for c in comment_cols:
        vals = tmp[c].tolist()
        all_comments.extend([v for v in vals if v and len(v.strip()) > 0])

    from collections import Counter
    top = Counter(all_comments).most_common(15)

    return {"comment_cols": comment_cols, "non_empty": non_empty, "top": top}

def build_tool_view(df_raw: pd.DataFrame, tool: str) -> pd.DataFrame:
    df = df_raw.copy()
    if df.shape[1] < 3:
        raise ValueError("The sheet must have at least 3 columns.")

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

@st.cache_data(ttl=86400)
def load_geojson_cached():
    """Load and cache GeoJSON data with error handling"""
    try:
        # Try multiple sources for robustness
        sources = [
            "https://raw.githubusercontent.com/awmc/afghanistan-geojson/master/afg_adm1.geojson",
            "https://raw.githubusercontent.com/datasets/geo-boundaries-world-110m/master/countries/AFG/ADM1.geojson"
        ]
        
        for url in sources:
            try:
                response = requests.get(url, timeout=10)
                if response.status_code == 200:
                    geojson = response.json()
                    if 'features' in geojson and len(geojson['features']) > 0:
                        return geojson
            except:
                continue
        
        # Fallback: create minimal geojson
        return {
            "type": "FeatureCollection",
            "features": []
        }
    except Exception as e:
        st.warning(f"Could not load GeoJSON: {str(e)}")
        return {
            "type": "FeatureCollection",
            "features": []
        }

def prepare_geojson_for_matching(geojson: dict, name_prop: str = "NAME", new_prop: str = "name_norm") -> dict:
    gj = geojson
    for f in gj.get("features", []):
        props = f.get("properties", {})
        raw_name = props.get(name_prop, props.get("name", props.get("NAME_1", "")))
        props[new_prop] = norm_text(raw_name)
        f["properties"] = props
    return gj

class BarChart(Flowable):
    """Custom flowable for bar charts in PDF"""
    def __init__(self, data, labels, width=400, height=200, colors=None):
        Flowable.__init__(self)
        self.data = data
        self.labels = labels
        self.width = width
        self.height = height
        self.colors = colors or [colors.HexColor('#667eea'), colors.HexColor('#764ba2')]

    def draw(self):
        canvas = self.canv
        canvas.saveState()
        
        max_val = max(self.data)
        bar_width = (self.width - 100) / len(self.data)
        
        # Draw bars
        for i, (val, label) in enumerate(zip(self.data, self.labels)):
            x = 50 + i * bar_width
            bar_height = (val / max_val) * (self.height - 50)
            color = self.colors[i % len(self.colors)]
            
            canvas.setFillColor(color)
            canvas.rect(x, 30, bar_width - 10, bar_height, fill=1)
            
            # Value label
            canvas.setFillColor(colors.black)
            canvas.setFont("Helvetica", 8)
            canvas.drawCentredString(x + bar_width/2 - 5, bar_height + 35, str(val))
            
            # X-axis label
            canvas.saveState()
            canvas.setFont("Helvetica", 7)
            canvas.translate(x + bar_width/2 - 5, 15)
            canvas.rotate(45)
            canvas.drawCentredString(0, 0, label[:15])
            canvas.restoreState()
        
        # Y-axis
        canvas.setStrokeColor(colors.black)
        canvas.setLineWidth(0.5)
        canvas.line(40, 30, 40, self.height - 20)
        canvas.line(40, 30, self.width - 30, 30)
        
        canvas.restoreState()

def make_pdf_report(
    tool_choice: str,
    filters: dict,
    kpis: dict,
    regional_summary: pd.DataFrame,
    province_summary: pd.DataFrame,
    comment_summary: dict,
    filtered_df: pd.DataFrame
) -> bytes:
    """Generate comprehensive PDF report"""
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
    
    # Custom styles
    styles.add(ParagraphStyle(
        name='CustomTitle',
        parent=styles['Title'],
        fontSize=24,
        textColor=colors.HexColor('#1E3A8A'),
        spaceAfter=30,
        alignment=TA_CENTER
    ))
    
    styles.add(ParagraphStyle(
        name='SectionHeader',
        parent=styles['Heading2'],
        fontSize=14,
        textColor=colors.HexColor('#667eea'),
        spaceAfter=12,
        spaceBefore=20
    ))
    
    story = []
    
    # Cover Page
    story.append(Spacer(1, 4*cm))
    story.append(Paragraph("SAMPLE TRACK ANALYTICS REPORT", styles['CustomTitle']))
    story.append(Spacer(1, 1*cm))
    story.append(Paragraph(f"Tool: {tool_choice}", styles['Heading2']))
    story.append(Paragraph(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M')}", styles['Normal']))
    story.append(Spacer(1, 2*cm))
    story.append(Paragraph("Ministry of Education", styles['Heading3']))
    story.append(Paragraph("Afghanistan", styles['Normal']))
    story.append(PageBreak())
    
    # Executive Summary
    story.append(Paragraph("EXECUTIVE SUMMARY", styles['CustomTitle']))
    story.append(Spacer(1, 0.5*cm))
    
    exec_data = [
        ["Metric", "Value", "Status"],
        ["Overall Progress", f"{kpis['overall_progress']:.1f}%", "🟢 Good" if kpis['overall_progress'] >= 75 else "🟡 Moderate" if kpis['overall_progress'] >= 50 else "🔴 Needs Attention"],
        ["Samples Checked", f"{kpis['total_checked']:,.0f} / {kpis['total_sample']:,.0f}", f"{kpis['total_checked']/kpis['total_sample']*100:.1f}%"],
        ["Approval Rate", f"{kpis['total_approved']:,.0f}", f"{(kpis['total_approved']/kpis['total_checked']*100 if kpis['total_checked']>0 else 0):.1f}%"],
        ["Rejection Rate", f"{kpis['total_rejected']:,.0f}", f"{(kpis['total_rejected']/kpis['total_checked']*100 if kpis['total_checked']>0 else 0):.1f}%"],
        ["Pending Review", f"{kpis['total_pending']:,.0f}", "In Progress"],
        ["Geographic Coverage", f"{filtered_df['Province'].nunique()} Provinces", f"{filtered_df['District'].nunique()} Districts"]
    ]
    
    exec_table = Table(exec_data, colWidths=[5*cm, 4*cm, 4*cm])
    exec_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#667eea')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#f8fafc')),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    story.append(exec_table)
    
    # Key Insights
    story.append(Paragraph("Key Insights", styles['SectionHeader']))
    
    insights = [
        f"Total target samples: {kpis['total_sample']:,.0f}",
        f"Overall completion rate: {kpis['overall_progress']:.1f}%",
        f"Top performing province: {province_summary.iloc[0]['Province'] if not province_summary.empty else 'N/A'} ({province_summary.iloc[0]['Progress']:.1f}% if not province_summary.empty else 'N/A')",
        f"Areas needing attention: {', '.join(province_summary[province_summary['Progress'] < 50]['Province'].head(3).tolist()) if not province_summary[province_summary['Progress'] < 50].empty else 'None'}",
        f"Data quality: {comment_summary['non_empty']} comments recorded"
    ]
    
    for insight in insights:
        story.append(ListItem(Paragraph(insight, styles['Normal']), bulletColor=colors.HexColor('#667eea')))
    
    story.append(PageBreak())
    
    # Detailed Analysis
    story.append(Paragraph("DETAILED ANALYSIS", styles['CustomTitle']))
    
    # Regional Performance
    story.append(Paragraph("Regional Performance", styles['SectionHeader']))
    if not regional_summary.empty:
        reg_data = [["Region", "Target", "Checked", "Progress %", "Status"]] + \
                   [[row['Region'], 
                     f"{row['Total_Sample_Size']:,.0f}", 
                     f"{row['Total_Checked']:,.0f}", 
                     f"{row['Progress']:.1f}%",
                     "🟢" if row['Progress'] >= 75 else "🟡" if row['Progress'] >= 50 else "🔴"]
                    for _, row in regional_summary.iterrows()]
        
        reg_table = Table(reg_data, colWidths=[3.5*cm, 2.5*cm, 2.5*cm, 2.5*cm, 1.5*cm])
        reg_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#764ba2')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BACKGROUND', (0, 1), (-1, -1), colors.whitesmoke),
            ('GRID', (0, 0), (-1, -1), 0.3, colors.grey),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        story.append(reg_table)
    
    # Top 10 Provinces
    story.append(Spacer(1, 1*cm))
    story.append(Paragraph("Top 10 Performing Provinces", styles['SectionHeader']))
    
    if not province_summary.empty:
        top_provinces = province_summary.nlargest(10, 'Progress')
        province_data = [["Rank", "Province", "Progress %", "Samples Checked", "Approval Rate"]] + \
                       [[str(i+1), 
                         row['Province'], 
                         f"{row['Progress']:.1f}%",
                         f"{row['Total_Checked']:,.0f}",
                         f"{(row['Approved']/row['Total_Checked']*100 if row['Total_Checked']>0 else 0):.1f}%"]
                        for i, (_, row) in enumerate(top_provinces.iterrows())]
        
        prov_table = Table(province_data, colWidths=[1.5*cm, 4*cm, 2.5*cm, 3*cm, 2.5*cm])
        prov_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#667eea')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#f8fafc')),
            ('GRID', (0, 0), (-1, -1), 0.3, colors.grey),
        ]))
        story.append(prov_table)
    
    # Comments Analysis
    if comment_summary['non_empty'] > 0:
        story.append(Spacer(1, 1*cm))
        story.append(Paragraph("Comments Analysis", styles['SectionHeader']))
        
        story.append(Paragraph(f"Total comments recorded: {comment_summary['non_empty']:,}", styles['Normal']))
        story.append(Paragraph(f"Comment columns detected: {len(comment_summary['comment_cols'])}", styles['Normal']))
        
        if comment_summary['top']:
            story.append(Spacer(1, 0.5*cm))
            story.append(Paragraph("Most Frequent Comments:", styles['Heading3']))
            
            comment_data = [["Comment", "Frequency"]] + \
                          [[text[:80] + "..." if len(text) > 80 else text, str(count)] 
                           for text, count in comment_summary['top'][:10]]
            
            comment_table = Table(comment_data, colWidths=[10*cm, 2*cm])
            comment_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('GRID', (0, 0), (-1, -1), 0.3, colors.grey),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ]))
            story.append(comment_table)
    
    # Statistical Summary
    story.append(PageBreak())
    story.append(Paragraph("STATISTICAL SUMMARY", styles['CustomTitle']))
    
    stats = [
        ["Metric", "Value", "Description"],
        ["Mean Progress", f"{filtered_df['Progress_Percentage'].mean():.1f}%", "Average progress across all districts"],
        ["Median Progress", f"{filtered_df['Progress_Percentage'].median():.1f}%", "Middle value of progress distribution"],
        ["Std Deviation", f"{filtered_df['Progress_Percentage'].std():.1f}%", "Variability in progress rates"],
        ["Completion Range", f"{filtered_df['Progress_Percentage'].min():.1f}% - {filtered_df['Progress_Percentage'].max():.1f}%", "Minimum to maximum progress"],
        ["Districts On Track", f"{(filtered_df['Progress_Status'] == 'On Track').sum():,}", "Districts with ≥75% progress"],
        ["Districts Critical", f"{(filtered_df['Progress_Status'] == 'Critical').sum():,}", "Districts with <50% progress"]
    ]
    
    stats_table = Table(stats, colWidths=[4*cm, 3*cm, 8*cm])
    stats_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#764ba2')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BACKGROUND', (0, 1), (-1, -1), colors.whitesmoke),
        ('GRID', (0, 0), (-1, -1), 0.3, colors.grey),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    story.append(stats_table)
    
    # Recommendations
    story.append(Spacer(1, 1*cm))
    story.append(Paragraph("RECOMMENDATIONS", styles['SectionHeader']))
    
    recommendations = [
        "Focus resources on provinces with progress below 50%",
        "Review and address frequent comments/issues",
        "Implement weekly progress monitoring for critical districts",
        "Consider reallocating samples from high-performing to low-performing areas",
        "Schedule follow-up assessments for districts with high rejection rates"
    ]
    
    for i, rec in enumerate(recommendations, 1):
        story.append(Paragraph(f"{i}. {rec}", styles['Normal']))
    
    # Footer
    story.append(Spacer(1, 2*cm))
    story.append(Paragraph("--- End of Report ---", ParagraphStyle(
        name='Footer',
        parent=styles['Normal'],
        fontSize=9,
        textColor=colors.grey,
        alignment=TA_CENTER
    )))
    story.append(Paragraph(f"Report generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", ParagraphStyle(
        name='Timestamp',
        parent=styles['Normal'],
        fontSize=8,
        textColor=colors.darkgrey,
        alignment=TA_CENTER
    )))
    
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
except Exception as e:
    st.error("Failed to load data from Google Sheet")
    st.stop()

# =========================
# Sidebar
# =========================
st.sidebar.markdown("## 🔧 Filters & Controls")

tool_choice = st.sidebar.selectbox(
    "Select Monitoring Tool",
    ["Total", "CBE", "PBs"],
    help="Choose the data source to analyze"
)

try:
    df = build_tool_view(df_sheet, tool_choice)
except Exception as e:
    st.error("Error processing data")
    st.stop()

# Region filter
selected_region = st.sidebar.selectbox(
    "Select Region",
    ["All"] + sorted(df["Region"].dropna().unique().tolist())
)

# Province filter
if selected_region != "All":
    province_options = ["All"] + sorted(df[df["Region"] == selected_region]["Province"].dropna().unique().tolist())
else:
    province_options = ["All"] + sorted(df["Province"].dropna().unique().tolist())

selected_province = st.sidebar.selectbox("Select Province", province_options)

# District filter
if selected_province != "All":
    district_options = ["All"] + sorted(df[df["Province"] == selected_province]["District"].dropna().unique().tolist())
elif selected_region != "All":
    district_options = ["All"] + sorted(df[df["Region"] == selected_region]["District"].dropna().unique().tolist())
else:
    district_options = ["All"] + sorted(df["District"].dropna().unique().tolist())

selected_district = st.sidebar.selectbox("Select District", district_options)

# Progress filter
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
st.markdown('<div class="section-header">📈 Performance Dashboard</div>', unsafe_allow_html=True)

total_sample = float(filtered_df["Total_Sample_Size"].sum())
total_received = float(filtered_df["Total_Received"].sum())
total_approved = float(filtered_df["Approved"].sum())
total_pending = float(filtered_df["Pending"].sum())
total_rejected = float(filtered_df["Rejected"].sum())
total_checked = float(filtered_df["Total_Checked"].sum())

overall_progress = (total_checked / total_sample * 100.0) if total_sample > 0 else 0.0
approval_rate = (total_approved / total_checked * 100.0) if total_checked > 0 else 0.0
rejection_rate = (total_rejected / total_checked * 100.0) if total_checked > 0 else 0.0

k1, k2, k3, k4 = st.columns(4)

with k1:
    st.markdown(f"""
    <div class="metric-card">
        <div class="kpi-label">🎯 TOTAL TARGET</div>
        <div class="kpi-value">{total_sample:,.0f}</div>
        <div class="kpi-change">Provinces: {filtered_df["Province"].nunique():,}</div>
        <div class="kpi-change">Districts: {filtered_df["District"].nunique():,}</div>
    </div>
    """, unsafe_allow_html=True)

with k2:
    progress_color = "#10B981" if overall_progress >= 75 else "#F59E0B" if overall_progress >= 50 else "#EF4444"
    st.markdown(f"""
    <div class="metric-card">
        <div class="kpi-label">📊 OVERALL PROGRESS</div>
        <div class="kpi-value">{overall_progress:.1f}%</div>
        <div class="kpi-change">Checked: {total_checked:,.0f}</div>
        <div class="kpi-change">Remaining: {max(total_sample-total_checked, 0):,.0f}</div>
    </div>
    """, unsafe_allow_html=True)

with k3:
    st.markdown(f"""
    <div class="metric-card">
        <div class="kpi-label">✅ APPROVALS</div>
        <div class="kpi-value">{total_approved:,.0f}</div>
        <div class="kpi-change">Approval Rate: {approval_rate:.1f}%</div>
        <div class="kpi-change">Rejected: {total_rejected:,.0f}</div>
    </div>
    """, unsafe_allow_html=True)

with k4:
    st.markdown(f"""
    <div class="metric-card">
        <div class="kpi-label">⏳ PENDING REVIEW</div>
        <div class="kpi-value">{total_pending:,.0f}</div>
        <div class="kpi-change">Rejection Rate: {rejection_rate:.1f}%</div>
        <div class="kpi-change">Received: {total_received:,.0f}</div>
    </div>
    """, unsafe_allow_html=True)

# =========================
# Maps
# =========================
st.markdown('<div class="section-header">🗺️ Geographic Analysis</div>', unsafe_allow_html=True)

# Load GeoJSON with progress indicator
with st.spinner('Loading map data...'):
    geojson_data = load_geojson_cached()
    
if geojson_data and 'features' in geojson_data and len(geojson_data['features']) > 0:
    geojson_data = prepare_geojson_for_matching(geojson_data)
    
    # Prepare province data for map
    prov_summary = filtered_df.groupby(["Province", "_prov_norm"], as_index=False).agg({
        "Total_Sample_Size":"sum",
        "Total_Checked":"sum",
        "Approved":"sum",
        "Rejected":"sum",
        "Pending":"sum"
    })
    prov_summary["Progress_Percentage"] = np.where(
        prov_summary["Total_Sample_Size"] > 0,
        (prov_summary["Total_Checked"] / prov_summary["Total_Sample_Size"] * 100.0),
        0
    ).round(1)
    
    map_left, map_right = st.columns(2)
    
    with map_left:
        st.markdown("##### Afghanistan - Province Level")
        fig_afg = px.choropleth(
            prov_summary,
            geojson=geojson_data,
            locations="_prov_norm",
            featureidkey="properties.name_norm",
            color="Progress_Percentage",
            hover_name="Province",
            hover_data={
                "Progress_Percentage": ":.1f%",
                "Total_Sample_Size": ":,.0f",
                "Total_Checked": ":,.0f",
                "Approved": ":,.0f",
                "Rejected": ":,.0f",
                "Pending": ":,.0f",
                "_prov_norm": False
            },
            color_continuous_scale="RdYlGn",
            range_color=[0, 100],
            title=f"{tool_choice} - Progress Distribution"
        )
        fig_afg.update_geos(
            fitbounds="locations",
            visible=False,
            bgcolor="rgba(0,0,0,0)",
            lakecolor="LightBlue",
            rivercolor="LightBlue"
        )
        fig_afg.update_layout(
            height=500,
            margin=dict(l=0, r=0, t=40, b=0),
            geo=dict(bgcolor='rgba(0,0,0,0)'),
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)'
        )
        st.plotly_chart(fig_afg, use_container_width=True)
    
    with map_right:
        st.markdown("##### Progress Heat Map")
        # Create bubble map for detailed view
        if not filtered_df.empty:
            fig_bubble = px.scatter_geo(
                filtered_df,
                lat=np.random.uniform(31, 37, len(filtered_df)),  # Approximate latitudes for Afghanistan
                lon=np.random.uniform(60, 75, len(filtered_df)),  # Approximate longitudes
                size="Total_Sample_Size",
                color="Progress_Percentage",
                hover_name="District",
                hover_data=["Province", "Total_Checked", "Approved", "Rejected"],
                size_max=30,
                color_continuous_scale="Viridis",
                title="Sample Distribution & Progress"
            )
            fig_bubble.update_geos(
                visible=True,
                resolution=50,
                showcountries=True,
                countrycolor="Black",
                showsubunits=True,
                subunitcolor="Blue"
            )
            fig_bubble.update_layout(height=500, margin=dict(l=0, r=0, t=40, b=0))
            st.plotly_chart(fig_bubble, use_container_width=True)
else:
    st.warning("Map data unavailable. Displaying tabular data instead.")
    st.dataframe(filtered_df.head(20), use_container_width=True)

# =========================
# Charts
# =========================
st.markdown('<div class="section-header">📊 Data Visualization</div>', unsafe_allow_html=True)

tab1, tab2, tab3, tab4 = st.tabs(["Progress Overview", "Status Analysis", "Regional Comparison", "Trend Analysis"])

with tab1:
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # Gauge chart
        fig_gauge = go.Figure(go.Indicator(
            mode="gauge+number+delta",
            value=overall_progress,
            domain={'x': [0, 1], 'y': [0, 1]},
            title={'text': f"{tool_choice} Overall Progress", 'font': {'size': 24}},
            delta={'reference': 70, 'increasing': {'color': "green"}},
            gauge={
                'axis': {'range': [None, 100], 'tickwidth': 1, 'tickcolor': "darkblue"},
                'bar': {'color': "darkblue"},
                'bgcolor': "white",
                'borderwidth': 2,
                'bordercolor': "gray",
                'steps': [
                    {'range': [0, 50], 'color': 'red'},
                    {'range': [50, 75], 'color': 'yellow'},
                    {'range': [75, 100], 'color': 'green'}],
                'threshold': {
                    'line': {'color': "red", 'width': 4},
                    'thickness': 0.75,
                    'value': 70}
            }
        ))
        fig_gauge.update_layout(height=400)
        st.plotly_chart(fig_gauge, use_container_width=True)
    
    with col2:
        # Progress distribution
        if not filtered_df.empty:
            status_dist = filtered_df['Progress_Status'].value_counts()
            fig_pie = px.pie(
                values=status_dist.values,
                names=status_dist.index,
                hole=0.5,
                color=status_dist.index,
                color_discrete_map={
                    'On Track': '#10B981',
                    'Behind Schedule': '#F59E0B',
                    'Critical': '#EF4444'
                }
            )
            fig_pie.update_layout(height=400, showlegend=True)
            st.plotly_chart(fig_pie, use_container_width=True)

with tab2:
    # Status breakdown
    status_data = pd.DataFrame({
        'Category': ['Approved', 'Pending', 'Rejected', 'Not Checked'],
        'Count': [total_approved, total_pending, total_rejected, max(total_sample - total_checked, 0)]
    })
    
    fig_bar = px.bar(
        status_data,
        x='Category',
        y='Count',
        color='Category',
        color_discrete_sequence=['#10B981', '#F59E0B', '#EF4444', '#6B7280'],
        text='Count'
    )
    fig_bar.update_layout(
        height=400,
        title="Sample Status Breakdown",
        xaxis_title="",
        yaxis_title="Count",
        showlegend=False
    )
    fig_bar.update_traces(texttemplate='%{text:,}', textposition='outside')
    st.plotly_chart(fig_bar, use_container_width=True)

with tab3:
    # Regional comparison
    if not filtered_df.empty:
        regional_data = filtered_df.groupby('Region').agg({
            'Total_Sample_Size': 'sum',
            'Total_Checked': 'sum',
            'Progress_Percentage': 'mean'
        }).reset_index()
        
        fig_region = px.bar(
            regional_data,
            x='Region',
            y='Progress_Percentage',
            color='Progress_Percentage',
            color_continuous_scale='RdYlGn',
            text='Progress_Percentage',
            hover_data=['Total_Sample_Size', 'Total_Checked']
        )
        fig_region.update_layout(
            height=400,
            title="Progress by Region",
            xaxis_title="Region",
            yaxis_title="Progress (%)",
            coloraxis_showscale=False
        )
        fig_region.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
        st.plotly_chart(fig_region, use_container_width=True)

with tab4:
    # Target vs Checked scatter
    if not filtered_df.empty:
        fig_scatter = px.scatter(
            filtered_df,
            x='Total_Sample_Size',
            y='Total_Checked',
            size='Total_Sample_Size',
            color='Progress_Percentage',
            hover_name='District',
            hover_data=['Province', 'Approved', 'Rejected', 'Pending'],
            color_continuous_scale='Viridis',
            size_max=30,
            trendline="lowess"
        )
        
        # Add diagonal line for perfect correlation
        max_val = max(filtered_df['Total_Sample_Size'].max(), filtered_df['Total_Checked'].max())
        fig_scatter.add_trace(go.Scatter(
            x=[0, max_val],
            y=[0, max_val],
            mode='lines',
            name='Target = Checked',
            line=dict(color='red', dash='dash')
        ))
        
        fig_scatter.update_layout(
            height=500,
            title="Target vs Checked Analysis",
            xaxis_title="Target Sample Size",
            yaxis_title="Samples Checked"
        )
        st.plotly_chart(fig_scatter, use_container_width=True)

# =========================
# Detailed Tables
# =========================
st.markdown('<div class="section-header">📋 Detailed Analysis</div>', unsafe_allow_html=True)

col1, col2 = st.columns(2)

with col1:
    st.markdown("##### 🏛️ Province Summary")
    
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
    province_summary["Approval_Rate"] = (province_summary["Approved"] / province_summary["Total_Checked"] * 100).round(1)
    province_summary = province_summary.fillna(0)
    
    # Format for display
    display_prov = province_summary.copy()
    display_prov["Total_Sample_Size"] = display_prov["Total_Sample_Size"].apply(lambda x: f"{x:,.0f}")
    display_prov["Total_Checked"] = display_prov["Total_Checked"].apply(lambda x: f"{x:,.0f}")
    display_prov["Progress"] = display_prov["Progress"].apply(lambda x: f"{x:.1f}%")
    display_prov["Approval_Rate"] = display_prov["Approval_Rate"].apply(lambda x: f"{x:.1f}%")
    
    st.dataframe(
        display_prov[["Province", "Total_Sample_Size", "Total_Checked", "Progress", "Approval_Rate"]]
        .sort_values("Progress", ascending=False),
        use_container_width=True,
        height=400
    )

with col2:
    st.markdown("##### 🏘️ District Performance")
    
    metric_sort = st.selectbox(
        "Sort by metric:",
        ["Progress_Percentage", "Total_Sample_Size", "Total_Checked", "Approved", "Rejected"],
        index=0
    )
    
    district_summary = filtered_df.groupby(["Province", "District"], as_index=False).agg({
        "Total_Sample_Size":"sum",
        "Total_Checked":"sum",
        "Approved":"sum",
        "Rejected":"sum",
        "Pending":"sum",
        "Progress_Percentage":"mean"
    }).round(2)
    
    # Add status indicator
    district_summary["Status"] = district_summary["Progress_Percentage"].apply(
        lambda x: "🟢" if x >= 75 else "🟡" if x >= 50 else "🔴"
    )
    
    display_dist = district_summary[["Province", "District", "Total_Sample_Size", 
                                    "Total_Checked", "Progress_Percentage", "Status"]]
    display_dist = display_dist.sort_values(metric_sort, ascending=False).head(30)
    
    st.dataframe(
        display_dist,
        use_container_width=True,
        height=400,
        column_config={
            "Progress_Percentage": st.column_config.ProgressColumn(
                "Progress %",
                help="Completion progress",
                format="%.1f%%",
                min_value=0,
                max_value=100,
            ),
            "Status": st.column_config.TextColumn("Status")
        }
    )

# =========================
# PDF Export
# =========================
st.markdown('<div class="section-header">📄 Report Export</div>', unsafe_allow_html=True)

comment_summary = summarize_comments(df_sheet)
regional_summary = filtered_df.groupby("Region", as_index=False).agg({
    "Total_Sample_Size":"sum",
    "Total_Checked":"sum",
    "Approved":"sum",
    "Rejected":"sum",
    "Pending":"sum"
})
regional_summary["Progress"] = (regional_summary["Total_Checked"] / regional_summary["Total_Sample_Size"] * 100).round(1)

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

export_col1, export_col2, export_col3 = st.columns([1, 2, 1])

with export_col1:
    if st.button("📊 Generate Comprehensive Report", type="primary", use_container_width=True):
        with st.spinner("Generating professional report..."):
            try:
                pdf_bytes = make_pdf_report(
                    tool_choice=tool_choice,
                    filters=filters_for_pdf,
                    kpis=kpis_for_pdf,
                    regional_summary=regional_summary,
                    province_summary=province_summary,
                    comment_summary=comment_summary,
                    filtered_df=filtered_df
                )
                
                now = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"SampleTrack_Report_{tool_choice}_{now}.pdf"
                
                st.success("Report generated successfully!")
                st.download_button(
                    label="📥 Download PDF Report",
                    data=pdf_bytes,
                    file_name=filename,
                    mime="application/pdf",
                    type="secondary",
                    use_container_width=True
                )
            except Exception as e:
                st.error(f"Error generating report: {str(e)}")

with export_col2:
    st.markdown("""
    <div class="hint">
    <b>Report Includes:</b>
    • Executive Summary with Key Metrics<br/>
    • Geographic Performance Analysis<br/>
    • Regional & Provincial Comparisons<br/>
    • Statistical Analysis & Trends<br/>
    • Comments & Feedback Summary<br/>
    • Actionable Recommendations<br/>
    • Professional Formatting & Design
    </div>
    """, unsafe_allow_html=True)

# =========================
# Footer
# =========================
st.markdown("---")

footer_col1, footer_col2, footer_col3 = st.columns(3)

with footer_col1:
    st.markdown(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

with footer_col2:
    st.markdown(f"**Tool:** {tool_choice} | **Records:** {len(filtered_df):,}")

with footer_col3:
    st.markdown(f"**Progress:** {overall_progress:.1f}% | **Coverage:** {filtered_df['Province'].nunique()} Provinces")

st.markdown(
    '<div style="text-align: center; color: #64748B; font-size: 0.8rem; margin-top: 2rem;">'
    'Sample Track Analytics Dashboard v2.0 © 2024 Ministry of Education, Afghanistan'
    '</div>',
    unsafe_allow_html=True
)
