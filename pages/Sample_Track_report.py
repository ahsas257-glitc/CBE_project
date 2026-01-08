import streamlit as st
import pandas as pd
import numpy as np
import altair as alt
import gspread
from google.oauth2.service_account import Credentials
from io import BytesIO
from datetime import datetime
from theme.theme import apply_theme

from docx import Document
from docx.shared import Pt
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet


st.set_page_config(page_title="Sample Track Report", layout="wide")
apply_theme()

st.title("Sample Track Report")

SPREADSHEET_KEY = "1lkztBZ4eG1BQx-52XgnA6w8YIiw-Sm85pTlQQziurfw"
WORKSHEET_NAME = "Sample_Track"


REGIONS = [
    "Central",
    "Central Highland",
    "East",
    "North",
    "North East",
    "South",
    "South East",
    "West",
]

PROVINCES = [
    "Badakhshan",
    "Badghis",
    "Baghlan",
    "Balkh",
    "Bamyan",
    "Daykundi",
    "Farah",
    "Faryab",
    "Ghazni",
    "Ghor",
    "Hilmand",
    "Hirat",
    "Jawzjan",
    "Kabul",
    "Kandahar",
    "Kapisa",
    "Khost",
    "Kunar",
    "Kunduz",
    "Laghman",
    "Logar",
    "Maidan Wardak",
    "Nangarhar",
    "Nimroz",
    "Nuristan",
    "Paktika",
    "Paktya",
    "Panjsher",
    "Parwan",
    "Samangan",
    "Sar-e-Pul",
    "Takhar",
    "Uruzgan",
    "Zabul",
]

PROVINCE_DISTRICTS = {
    "Badakhshan": ["Darayem", "Jorm", "Shahr-e-Buzorg", "Teshkan", "Warduj"],
    "Badghis": ["Ab Kamari", "Jawand", "Qadis", "Qala-e-Naw"],
    "Baghlan": ["Baghlan-e-Jadid", "Nahrin", "Pul-e-Khumri", "Tala Wa Barfak"],
    "Balkh": ["Alburz", "Balkh", "Chahi", "Charkent", "Kaldar", "Khulm", "Mazar-e-Sharif", "Nahr-e-Shahi"],
    "Bamyan": ["Kahmard", "Sayghan", "Shibar", "Waras", "Yakawlang"],
    "Daykundi": ["Ashtarlay", "Kajran", "Khadir", "Kiti", "Nawmish", "Nili", "Shahrestan"],
    "Farah": ["Lash-e-Juwayn", "Qala-e-Kah", "Shibkoh"],
    "Faryab": ["Andkhoy", "Bilcheragh", "Dawlat Abad", "Garzewan", "Khan-e-Char Bagh", "Khwaja Sabz Posh", "Qaysar", "Qurghan", "Shirin Tagab"],
    "Ghazni": ["Ab Band", "Ajristan", "Deh Yak", "Gelan", "Ghazni", "Khwaja Umari", "Malistan", "Rashidan", "Waghaz", "Wal-e-Muhammad-e-Shahid", "Zanakhan"],
    "Ghor": ["Chaghcharan", "Charsadra", "Dawlatyar", "Feroz Koh", "Morghab", "Saghar", "Taywarah", "Tolak"],
    "Hilmand": ["Lashkargah"],
    "Hirat": ["Adraskan", "Hirat", "Shindand", "Zer-i Koh"],
    "Jawzjan": ["Aqcha", "Darzab", "Fayzabad", "Khamyab", "Khanaqa", "Khwaja Dukoh", "Mardyan", "Qarqin", "Qush Tepa", "Shiberghan"],
    "Kabul": ["Bagrami", "Kabul", "Khak-e-Jabbar", "Musahi", "Surobi"],
    "Kandahar": ["Arghandab", "Arghestan", "Kandahar", "Khakrez"],
    "Kapisa": ["Hisa-e-Awal-e-Kohistan", "Hisa-e-Duwum-e-Kohistan", "Koh Band", "Mahmood-e-Raqi", "Tagab"],
    "Khost": ["Mandozayi", "Musa Khel", "Nadir Shah Kot", "Qalandar", "Sabari", "Tani", "Terezayi"],
    "Kunar": ["Dangam"],
    "Kunduz": ["Ali Abad", "Aqtash", "Chahar Darah", "Dasht-e-Archi", "Qala-e-Zal"],
    "Laghman": ["Badpakh", "Dawlatshah", "Mehtarlam", "Qarghayi"],
    "Logar": ["Azra"],
    "Maidan Wardak": ["Chak-e-Wardak", "Maydan Shahr", "Saydabad"],
    "Nangarhar": ["Deh Bala", "Jalalabad", "Kama", "Khogyani", "Rodat"],
    "Nimroz": ["Zaranj"],
    "Nuristan": ["Duab", "Kamdesh", "Mandol", "Wama", "Waygal"],
    "Paktika": ["Dila", "Omna", "Sar Rawzah", "Surobi", "Yahya Khel", "Yosuf Khel", "Zarghun Shahr"],
    "Paktya": ["Ahmadaba", "Chamkani", "Dand Wa Patan", "Garde Serai", "Jaji", "Jani Khel", "Rohanibaba", "Sayed Karam", "Zadran", "Zurmat"],
    "Panjsher": ["Anawa", "Bazarak"],
    "Parwan": ["Bagram", "Koh-e-Safi", "Salang", "Shinwari"],
    "Samangan": ["Aybak", "Feroz Nakhchir", "Hazrat-e-Sultan", "Khulm"],
    "Sar-e-Pul": ["Gosfandi", "Sayad"],
    "Takhar": ["Dasht-e-Qala", "Farkhar", "Kalafgan", "Khwaja Ghar", "Yangi Qala"],
    "Uruzgan": ["Chora", "Khas Uruzgan", "Tirinkot"],
    "Zabul": ["Arghandab", "Mizan", "Nawbahar", "Qalat", "Tarnak Wa Jaldak"],
}


@st.cache_data(ttl=300)
def load_sample_track() -> pd.DataFrame:
    from googleapiclient.discovery import build

    scopes = ["https://www.googleapis.com/auth/spreadsheets.readonly"]
    creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scopes)

    service = build("sheets", "v4", credentials=creds, cache_discovery=False)

    resp = service.spreadsheets().get(
        spreadsheetId=SPREADSHEET_KEY,
        ranges=[WORKSHEET_NAME],
        includeGridData=True,
        fields="sheets(data(rowData(values(effectiveValue,userEnteredValue,userEnteredFormat(backgroundColor)))))"
    ).execute()

    sheets = resp.get("sheets", [])
    if not sheets:
        return pd.DataFrame()

    data_blocks = sheets[0].get("data", [])
    if not data_blocks:
        return pd.DataFrame()

    row_data = data_blocks[0].get("rowData", [])
    if len(row_data) < 2:
        return pd.DataFrame()

    def cell_text(v):
        if not v:
            return ""
        ev = v.get("effectiveValue") or {}
        if "stringValue" in ev:
            return str(ev["stringValue"])
        if "numberValue" in ev:
            n = ev["numberValue"]
            if isinstance(n, float) and n.is_integer():
                return str(int(n))
            return str(n)
        if "boolValue" in ev:
            return "TRUE" if ev["boolValue"] else "FALSE"
        if "formulaValue" in ev:
            return str(ev["formulaValue"])
        uev = v.get("userEnteredValue") or {}
        if "stringValue" in uev:
            return str(uev["stringValue"])
        if "numberValue" in uev:
            return str(uev["numberValue"])
        return ""

    def is_target_bg(v, tol=0.02):
        fmt = (v or {}).get("userEnteredFormat") or {}
        bg = fmt.get("backgroundColor")
        if not bg:
            return False
        r = float(bg.get("red", 1.0))
        g = float(bg.get("green", 1.0))
        b = float(bg.get("blue", 1.0))

        tr, tg, tb = (201/255.0, 233/255.0, 231/255.0)
        return (abs(r - tr) <= tol) and (abs(g - tg) <= tol) and (abs(b - tb) <= tol)

    header_vals = row_data[0].get("values", [])
    header = []
    for i, v in enumerate(header_vals):
        h = cell_text(v).strip()
        header.append(h if h else f"col_{i}")

    rows = []
    for r in row_data[1:]:
        vals = r.get("values", [])

        if any(is_target_bg(v) for v in vals):
            continue

        row = [cell_text(vals[i]) if i < len(vals) else "" for i in range(len(header))]

        if all(str(x).strip() == "" for x in row):
            continue

        rows.append(row)

    df = pd.DataFrame(rows, columns=[c.strip() for c in header])
    df.columns = [c.strip() for c in df.columns]
    return df



def to_number(series: pd.Series) -> pd.Series:
    s = series.astype(str).str.replace(",", "", regex=False)
    s = s.str.replace(r"[^0-9\.\-]", "", regex=True)
    return pd.to_numeric(s, errors="coerce")


def extract_percent(series: pd.Series) -> pd.Series:
    s = series.astype(str).str.extract(r"(\d+(?:\.\d+)?)\s*%")[0]
    return pd.to_numeric(s, errors="coerce")


def safe_sum(s: pd.Series) -> float:
    return float(np.nan_to_num(s, nan=0.0).sum())


def validate_admin_structure(d: pd.DataFrame) -> pd.DataFrame:
    x = d.copy()
    x["Region"] = x["Region"].astype(str).str.strip()
    x["Province"] = x["Province"].astype(str).str.strip()
    x["District"] = x["District"].astype(str).str.strip()

    issues = []

    bad_regions = x.loc[
        ~x["Region"].isin(REGIONS) & x["Region"].ne("") & x["Region"].str.lower().ne("nan"),
        ["Region"]
    ].drop_duplicates()
    for v in bad_regions["Region"].tolist():
        issues.append({"Type": "Invalid Region", "Province": "", "District": "", "Value": v})

    bad_prov = x.loc[
        ~x["Province"].isin(PROVINCES) & x["Province"].ne("") & x["Province"].str.lower().ne("nan"),
        ["Province"]
    ].drop_duplicates()
    for v in bad_prov["Province"].tolist():
        issues.append({"Type": "Invalid Province", "Province": "", "District": "", "Value": v})

    for prov, grp in x.groupby("Province", dropna=False):
        prov = str(prov).strip()
        if prov in PROVINCE_DISTRICTS:
            valid_d = set(PROVINCE_DISTRICTS[prov])
            bad_d = grp.loc[
                ~grp["District"].isin(valid_d) & grp["District"].ne("") & grp["District"].str.lower().ne("nan"),
                ["District"]
            ].drop_duplicates()
            for v in bad_d["District"].tolist():
                issues.append({"Type": "Invalid District for Province", "Province": prov, "District": "", "Value": v})

    return pd.DataFrame(issues)


def df_to_docx_table(doc: Document, df: pd.DataFrame, title: str, max_rows: int = 50):
    doc.add_heading(title, level=2)
    df2 = df.copy()
    if len(df2) > max_rows:
        df2 = df2.head(max_rows)
    df2 = df2.fillna("")
    table = doc.add_table(rows=1, cols=len(df2.columns))
    hdr = table.rows[0].cells
    for i, c in enumerate(df2.columns):
        hdr[i].text = str(c)
    for _, row in df2.iterrows():
        cells = table.add_row().cells
        for i, c in enumerate(df2.columns):
            cells[i].text = str(row[c])
    doc.add_paragraph("")


def build_word_report(meta: dict, kpis: dict, prov: pd.DataFrame, dist: pd.DataFrame, issues: pd.DataFrame) -> bytes:
    doc = Document()
    doc.add_heading("Sample Track Report", level=1)

    p = doc.add_paragraph()
    p.add_run("Generated on: ").bold = True
    p.add_run(meta["generated_on"])

    p = doc.add_paragraph()
    p.add_run("Filters: ").bold = True
    p.add_run(f"Region={meta['region']} | Province={meta['province']} | District={meta['district']}")

    doc.add_paragraph("")

    doc.add_heading("Key Indicators", level=2)
    for k, v in kpis.items():
        line = doc.add_paragraph()
        line.add_run(f"{k}: ").bold = True
        line.add_run(str(v))

    doc.add_paragraph("")

    df_to_docx_table(doc, prov, "Province Summary", max_rows=50)
    df_to_docx_table(doc, dist, "District Summary (Top 50)", max_rows=50)

    if not issues.empty:
        df_to_docx_table(doc, issues, "Data Issues", max_rows=200)

    bio = BytesIO()
    doc.save(bio)
    bio.seek(0)
    return bio.getvalue()


def build_pdf_report(meta: dict, kpis: dict, prov: pd.DataFrame, dist: pd.DataFrame, issues: pd.DataFrame) -> bytes:
    styles = getSampleStyleSheet()
    story = []
    story.append(Paragraph("Sample Track Report", styles["Title"]))
    story.append(Spacer(1, 10))
    story.append(Paragraph(f"Generated on: {meta['generated_on']}", styles["Normal"]))
    story.append(Paragraph(f"Filters: Region={meta['region']} | Province={meta['province']} | District={meta['district']}", styles["Normal"]))
    story.append(Spacer(1, 12))

    story.append(Paragraph("Key Indicators", styles["Heading2"]))
    kpi_table_data = [["Indicator", "Value"]] + [[k, str(v)] for k, v in kpis.items()]
    t = Table(kpi_table_data, hAlign="LEFT")
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E8F6FB")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.black),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    story.append(t)
    story.append(Spacer(1, 14))

    def df_to_pdf_table(title: str, df: pd.DataFrame, max_rows: int = 40):
        story.append(Paragraph(title, styles["Heading2"]))
        df2 = df.copy()
        if len(df2) > max_rows:
            df2 = df2.head(max_rows)
        df2 = df2.fillna("")
        data = [list(df2.columns)] + df2.astype(str).values.tolist()
        tbl = Table(data, hAlign="LEFT")
        tbl.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E8F6FB")),
            ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
            ("FONTSIZE", (0, 0), (-1, -1), 7),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ]))
        story.append(tbl)
        story.append(Spacer(1, 14))

    df_to_pdf_table("Province Summary (Top 40)", prov, max_rows=40)
    df_to_pdf_table("District Summary (Top 40)", dist, max_rows=40)

    if not issues.empty:
        df_to_pdf_table("Data Issues (Top 100)", issues, max_rows=100)

    bio = BytesIO()
    doc = SimpleDocTemplate(bio, pagesize=A4, rightMargin=24, leftMargin=24, topMargin=28, bottomMargin=28)
    doc.build(story)
    bio.seek(0)
    return bio.getvalue()


df = load_sample_track()
if df.empty:
    st.error("No data found in Sample_Track.")
    st.stop()

expected_cols = [
    "Region", "Province", "Disrtict",
    "CBE-Sample Size", "PBs_sample size",
    "CBE_Data Received", "PBs_Data Received",
    "Total checked", "Approved", "Pending", "Rejected", "Not checked",
    "Unable to visit-CBE", "Unable to visit-PBs",
    "Remainig", "Progress", "# of Enumerators", "Comments"
]

for c in expected_cols:
    if c not in df.columns:
        df[c] = ""

df["Region"] = df["Region"].astype(str).str.strip()
df["Province"] = df["Province"].astype(str).str.strip()
df["District"] = df["Disrtict"].astype(str).str.strip()

df = df[~df["District"].str.endswith(" Total", na=False)]
df = df[~df["Province"].str.endswith(" Total", na=False)]
df = df[~df["Region"].str.endswith(" Total", na=False)]

df["Is_Total_Row"] = (
    df["Province"].str.lower().eq("total")
    | df["District"].str.lower().eq("total")
    | df["Region"].str.lower().eq("total")
)

base = df[~df["Is_Total_Row"]].copy()

base["CBE_Sample"] = to_number(base["CBE-Sample Size"])
base["PB_Sample"] = to_number(base["PBs_sample size"])
base["CBE_Received"] = to_number(base["CBE_Data Received"])
base["PB_Received"] = to_number(base["PBs_Data Received"])
base["Total_Checked"] = to_number(base["Total checked"])
base["Approved"] = to_number(base["Approved"])
base["Pending"] = to_number(base["Pending"])
base["Rejected"] = to_number(base["Rejected"])
base["Not_Checked"] = to_number(base["Not checked"])
base["Unable_CBE"] = to_number(base["Unable to visit-CBE"])
base["Unable_PB"] = to_number(base["Unable to visit-PBs"])
base["Remaining"] = to_number(base["Remainig"])
base["Progress_Pct"] = extract_percent(base["Progress"])
base["Enumerators"] = to_number(base["# of Enumerators"])


st.sidebar.header("Filters")
regions = ["All"] + REGIONS
sel_region = st.sidebar.selectbox("Region", regions)

fdf = base.copy()
if sel_region != "All":
    fdf = fdf[fdf["Region"].astype(str) == sel_region]

provinces_list = ["All"] + sorted([p for p in fdf["Province"].dropna().unique().tolist() if p and p.lower() != "nan"])
sel_province = st.sidebar.selectbox("Province", provinces_list)

if sel_province != "All":
    fdf = fdf[fdf["Province"].astype(str) == sel_province]

districts_list = ["All"] + sorted([d for d in fdf["District"].dropna().unique().tolist() if d and d.lower() != "nan"])
sel_district = st.sidebar.selectbox("District", districts_list)

if sel_district != "All":
    fdf = fdf[fdf["District"].astype(str) == sel_district]


issues_df = validate_admin_structure(fdf)

k1, k2, k3, k4 = st.columns(4)
k1.metric("Rows", f"{len(fdf):,}")
k2.metric("Provinces", f"{fdf['Province'].nunique():,}")
k3.metric("Districts", f"{fdf['District'].nunique():,}")
k4.metric("Avg Progress (%)", f"{np.nanmean(fdf['Progress_Pct']):.1f}" if fdf["Progress_Pct"].notna().any() else "N/A")

k5, k6, k7, k8 = st.columns(4)
k5.metric("CBE Sample", f"{safe_sum(fdf['CBE_Sample']):,.0f}")
k6.metric("PB Sample", f"{safe_sum(fdf['PB_Sample']):,.0f}")
k7.metric("Approved", f"{safe_sum(fdf['Approved']):,.0f}")
k8.metric("Remaining", f"{safe_sum(fdf['Remaining']):,.0f}")

st.divider()

prov = (
    fdf.groupby(["Region", "Province"], dropna=False)
    .agg(
        Districts=("District", "nunique"),
        CBE_Sample=("CBE_Sample", "sum"),
        PB_Sample=("PB_Sample", "sum"),
        CBE_Received=("CBE_Received", "sum"),
        PB_Received=("PB_Received", "sum"),
        Total_Checked=("Total_Checked", "sum"),
        Approved=("Approved", "sum"),
        Pending=("Pending", "sum"),
        Rejected=("Rejected", "sum"),
        Not_Checked=("Not_Checked", "sum"),
        Unable_CBE=("Unable_CBE", "sum"),
        Unable_PB=("Unable_PB", "sum"),
        Remaining=("Remaining", "sum"),
        Avg_Progress=("Progress_Pct", "mean"),
        Enumerators=("Enumerators", "max"),
    )
    .reset_index()
)

prov["Avg_Progress"] = prov["Avg_Progress"].round(1)

dist = (
    fdf.groupby(["Region", "Province", "District"], dropna=False)
    .agg(
        CBE_Sample=("CBE_Sample", "sum"),
        PB_Sample=("PB_Sample", "sum"),
        CBE_Received=("CBE_Received", "sum"),
        PB_Received=("PB_Received", "sum"),
        Total_Checked=("Total_Checked", "sum"),
        Approved=("Approved", "sum"),
        Pending=("Pending", "sum"),
        Rejected=("Rejected", "sum"),
        Not_Checked=("Not_Checked", "sum"),
        Unable_CBE=("Unable_CBE", "sum"),
        Unable_PB=("Unable_PB", "sum"),
        Remaining=("Remaining", "sum"),
        Progress=("Progress_Pct", "mean"),
    )
    .reset_index()
)

dist["Progress"] = dist["Progress"].round(1)

st.subheader("Province Overview")
metric_options = [
    "Approved", "Remaining", "Pending", "Rejected", "Total_Checked",
    "CBE_Received", "PB_Received", "CBE_Sample", "PB_Sample", "Avg_Progress"
]
metric = st.sidebar.selectbox("Chart Metric", metric_options, index=0)

if metric == "Avg_Progress":
    yfield = "Avg_Progress:Q"
    ytitle = "Average Progress (%)"
else:
    yfield = f"{metric}:Q"
    ytitle = metric.replace("_", " ")

chart = (
    alt.Chart(prov)
    .mark_bar()
    .encode(
        x=alt.X("Province:N", sort="-y", title="Province"),
        y=alt.Y(yfield, title=ytitle),
        tooltip=[
            "Region", "Province", "Districts",
            "CBE_Sample", "PB_Sample",
            "CBE_Received", "PB_Received",
            "Approved", "Pending", "Rejected", "Not_Checked",
            "Unable_CBE", "Unable_PB",
            "Remaining", "Avg_Progress",
            "Enumerators",
        ],
    )
    .interactive()
)

st.altair_chart(chart, use_container_width=True)

st.subheader("Top Districts")
top_metric = st.sidebar.selectbox("Top Districts By", ["Approved", "Remaining", "Pending", "Rejected", "Total_Checked", "Progress"], index=0)

if top_metric == "Progress":
    dist_sorted = dist.sort_values("Progress", ascending=False).head(30)
    dy = alt.Y("Progress:Q", title="Average Progress (%)")
else:
    dist_sorted = dist.sort_values(top_metric, ascending=False).head(30)
    dy = alt.Y(f"{top_metric}:Q", title=top_metric)

dchart = (
    alt.Chart(dist_sorted)
    .mark_bar()
    .encode(
        x=alt.X("District:N", sort="-y", title="District"),
        y=dy,
        tooltip=["Region", "Province", "District", "Approved", "Remaining", "Pending", "Rejected", "Total_Checked", "Progress"],
    )
    .interactive()
)

st.altair_chart(dchart, use_container_width=True)

st.divider()

t1, t2 = st.columns(2)
with t1:
    st.subheader("Province Summary Table")
    st.dataframe(prov.sort_values(metric if metric != "Avg_Progress" else "Avg_Progress", ascending=False), use_container_width=True, height=420)
with t2:
    st.subheader("District Summary Table")
    st.dataframe(dist.sort_values(top_metric if top_metric != "Progress" else "Progress", ascending=False), use_container_width=True, height=420)

if not issues_df.empty:
    st.divider()
    st.subheader("Data Issues")
    st.dataframe(issues_df, use_container_width=True, height=300)

st.divider()
st.subheader("Export Official Report")

meta = {
    "generated_on": datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
    "region": sel_region,
    "province": sel_province,
    "district": sel_district,
}

kpis = {
    "Rows (Filtered)": f"{len(fdf):,}",
    "Regions": f"{fdf['Region'].nunique():,}",
    "Provinces": f"{fdf['Province'].nunique():,}",
    "Districts": f"{fdf['District'].nunique():,}",
    "Average Progress (%)": f"{np.nanmean(fdf['Progress_Pct']):.1f}" if fdf["Progress_Pct"].notna().any() else "N/A",
    "CBE Sample": f"{safe_sum(fdf['CBE_Sample']):,.0f}",
    "PB Sample": f"{safe_sum(fdf['PB_Sample']):,.0f}",
    "Approved": f"{safe_sum(fdf['Approved']):,.0f}",
    "Remaining": f"{safe_sum(fdf['Remaining']):,.0f}",
}

prov_for_report = prov.sort_values("Approved", ascending=False)
dist_for_report = dist.sort_values("Approved", ascending=False)

pdf_bytes = build_pdf_report(meta, kpis, prov_for_report, dist_for_report, issues_df)
docx_bytes = build_word_report(meta, kpis, prov_for_report, dist_for_report, issues_df)

c1, c2 = st.columns(2)
with c1:
    st.download_button(
        "Download PDF Report",
        data=pdf_bytes,
        file_name="Sample_Track_Report.pdf",
        mime="application/pdf"
    )
with c2:
    st.download_button(
        "Download Word Report",
        data=docx_bytes,
        file_name="Sample_Track_Report.docx",
        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )
