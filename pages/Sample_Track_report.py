import streamlit as st
import pandas as pd
import numpy as np
import altair as alt
import gspread
from google.oauth2.service_account import Credentials
from theme.theme import apply_theme

st.set_page_config(page_title="Sample Track Report", layout="wide")
apply_theme()

st.title("Sample Track Report")

SPREADSHEET_KEY = "1lkztBZ4eG1BQx-52XgnA6w8YIiw-Sm85pTlQQziurfw"
WORKSHEET_NAME = "Sample_Track"

@st.cache_data(ttl=300)
def load_sample_track() -> pd.DataFrame:
    scopes = ["https://www.googleapis.com/auth/spreadsheets.readonly"]
    creds = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=scopes
    )
    client = gspread.authorize(creds)
    ws = client.open_by_key(SPREADSHEET_KEY).worksheet(WORKSHEET_NAME)

    values = ws.get_all_values()
    if not values or len(values) < 2:
        return pd.DataFrame()

    header = values[0]
    data = values[1:]

    header = [h.strip() if h else f"col_{i}" for i, h in enumerate(header)]
    df = pd.DataFrame(data, columns=header)

    df.columns = [c.strip() for c in df.columns]
    return df


def to_number(series: pd.Series) -> pd.Series:
    s = series.astype(str).str.replace(",", "", regex=False)
    s = s.str.replace(r"[^0-9\.\-]", "", regex=True)
    return pd.to_numeric(s, errors="coerce")

def extract_percent(series: pd.Series) -> pd.Series:
    s = series.astype(str).str.extract(r"(\d+(?:\.\d+)?)\s*%")[0]
    return pd.to_numeric(s, errors="coerce")

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

df["CBE_Sample"] = to_number(df["CBE-Sample Size"])
df["PB_Sample"] = to_number(df["PBs_sample size"])
df["CBE_Received"] = to_number(df["CBE_Data Received"])
df["PB_Received"] = to_number(df["PBs_Data Received"])
df["Total_Checked"] = to_number(df["Total checked"])
df["Approved"] = to_number(df["Approved"])
df["Pending"] = to_number(df["Pending"])
df["Rejected"] = to_number(df["Rejected"])
df["Not_Checked"] = to_number(df["Not checked"])
df["Unable_CBE"] = to_number(df["Unable to visit-CBE"])
df["Unable_PB"] = to_number(df["Unable to visit-PBs"])
df["Remaining"] = to_number(df["Remainig"])
df["Progress_Pct"] = extract_percent(df["Progress"])
df["Enumerators"] = to_number(df["# of Enumerators"])

df["Is_Total_Row"] = (
    df["Province"].str.lower().eq("total")
    | df["District"].str.lower().eq("total")
    | df["Region"].str.lower().eq("total")
)

base = df[~df["Is_Total_Row"]].copy()

st.sidebar.header("Filters")
regions = ["All"] + sorted([r for r in base["Region"].dropna().unique().tolist() if r and r.lower() != "nan"])
sel_region = st.sidebar.selectbox("Region", regions)

fdf = base.copy()
if sel_region != "All":
    fdf = fdf[fdf["Region"].astype(str) == sel_region]

provinces = ["All"] + sorted([p for p in fdf["Province"].dropna().unique().tolist() if p and p.lower() != "nan"])
sel_province = st.sidebar.selectbox("Province", provinces)

if sel_province != "All":
    fdf = fdf[fdf["Province"].astype(str) == sel_province]

districts = ["All"] + sorted([d for d in fdf["District"].dropna().unique().tolist() if d and d.lower() != "nan"])
sel_district = st.sidebar.selectbox("District", districts)

if sel_district != "All":
    fdf = fdf[fdf["District"].astype(str) == sel_district]

def safe_sum(s: pd.Series) -> float:
    return float(np.nan_to_num(s, nan=0.0).sum())

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

st.subheader("Province Overview")

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
            "Region", "Province",
            "Districts",
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

st.divider()

st.subheader("Downloads")

def to_csv_bytes(d: pd.DataFrame) -> bytes:
    return d.to_csv(index=False).encode("utf-8-sig")

b1, b2, b3 = st.columns(3)
with b1:
    st.download_button("Download Filtered Data (CSV)", data=to_csv_bytes(fdf), file_name="sample_track_filtered.csv", mime="text/csv")
with b2:
    st.download_button("Download Province Summary (CSV)", data=to_csv_bytes(prov), file_name="sample_track_province_summary.csv", mime="text/csv")
with b3:
    st.download_button("Download District Summary (CSV)", data=to_csv_bytes(dist), file_name="sample_track_district_summary.csv", mime="text/csv")
