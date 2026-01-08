import streamlit as st
import pandas as pd
import numpy as np
import altair as alt

st.set_page_config(page_title="Auto Report Dashboard", layout="wide")

st.title("📊 Automated Regional Report (Google Sheet → Streamlit)")

# 1) Put your published CSV link here (Publish to web -> CSV)
SHEET_CSV_URL = st.secrets.get("SHEET_CSV_URL", "")

st.sidebar.header("Data Source")

use_manual_url = st.sidebar.checkbox("Use manual CSV URL", value=(SHEET_CSV_URL == ""))
if use_manual_url:
    SHEET_CSV_URL = st.sidebar.text_input("Paste Published CSV URL", value=SHEET_CSV_URL)

@st.cache_data(ttl=300)
def load_data(url: str) -> pd.DataFrame:
    if not url:
        return pd.DataFrame()
    df = pd.read_csv(url)
    # Standardize columns (trim spaces)
    df.columns = [c.strip() for c in df.columns]
    return df

df = load_data(SHEET_CSV_URL)

if df.empty:
    st.warning("CSV URL را وارد کن یا در Streamlit secrets مقدار SHEET_CSV_URL را بگذار.")
    st.stop()

st.success(f"Loaded rows: {len(df):,} | columns: {len(df.columns)}")

# ---- Configure your key columns here ----
# Change these names to match your sheet columns exactly
REGION_COL   = "Region"
PROVINCE_COL = "Province"
DISTRICT_COL = "District"

# Numeric / metric columns (auto-detect numeric)
numeric_cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
date_cols = [c for c in df.columns if "date" in c.lower()]

# Basic checks
missing = [c for c in [REGION_COL, PROVINCE_COL, DISTRICT_COL] if c not in df.columns]
if missing:
    st.error(
        "این ستون‌ها در شیت پیدا نشد: "
        + ", ".join(missing)
        + "\n\nلطفاً نام دقیق ستون‌ها را در کد (REGION_COL/PROVINCE_COL/DISTRICT_COL) برابر با شیت تنظیم کن."
    )
    st.stop()

# --- Sidebar Filters ---
st.sidebar.header("Filters")

regions = ["All"] + sorted(df[REGION_COL].dropna().astype(str).unique().tolist())
sel_region = st.sidebar.selectbox("Region", regions)

fdf = df.copy()
if sel_region != "All":
    fdf = fdf[fdf[REGION_COL].astype(str) == sel_region]

provinces = ["All"] + sorted(fdf[PROVINCE_COL].dropna().astype(str).unique().tolist())
sel_province = st.sidebar.selectbox("Province (ولایت)", provinces)

if sel_province != "All":
    fdf = fdf[fdf[PROVINCE_COL].astype(str) == sel_province]

districts = ["All"] + sorted(fdf[DISTRICT_COL].dropna().astype(str).unique().tolist())
sel_district = st.sidebar.selectbox("District (ولسوالی)", districts)

if sel_district != "All":
    fdf = fdf[fdf[DISTRICT_COL].astype(str) == sel_district]

st.sidebar.header("Charts")
metric = st.sidebar.selectbox(
    "Metric (عدد/شاخص) برای چارت",
    options=(numeric_cols if numeric_cols else df.columns),
)

# If metric is not numeric, try to make a count chart instead
is_metric_numeric = metric in numeric_cols

# --- KPIs ---
c1, c2, c3, c4 = st.columns(4)

c1.metric("Rows (Filtered)", f"{len(fdf):,}")
c2.metric("Regions", f"{fdf[REGION_COL].nunique():,}")
c3.metric("Provinces", f"{fdf[PROVINCE_COL].nunique():,}")
c4.metric("Districts", f"{fdf[DISTRICT_COL].nunique():,}")

st.divider()

# --- Aggregations ---
# Province summary
if is_metric_numeric:
    prov_summary = (
        fdf.groupby(PROVINCE_COL, dropna=False)[metric]
        .agg(["count", "sum", "mean"])
        .reset_index()
        .sort_values("sum", ascending=False)
    )
else:
    prov_summary = (
        fdf.groupby(PROVINCE_COL, dropna=False)
        .size()
        .reset_index(name="count")
        .sort_values("count", ascending=False)
    )

# District summary
if is_metric_numeric:
    dist_summary = (
        fdf.groupby([PROVINCE_COL, DISTRICT_COL], dropna=False)[metric]
        .agg(["count", "sum", "mean"])
        .reset_index()
        .sort_values("sum", ascending=False)
    )
else:
    dist_summary = (
        fdf.groupby([PROVINCE_COL, DISTRICT_COL], dropna=False)
        .size()
        .reset_index(name="count")
        .sort_values("count", ascending=False)
    )

# --- Charts (Altair) ---
st.subheader("📌 Province-level Chart")

if is_metric_numeric:
    chart_df = prov_summary.rename(columns={"sum": "Total", "mean": "Average", "count": "Count"})
    bar = (
        alt.Chart(chart_df)
        .mark_bar()
        .encode(
            x=alt.X(f"{PROVINCE_COL}:N", sort="-y", title="Province"),
            y=alt.Y("Total:Q", title=f"Total {metric}"),
            tooltip=[PROVINCE_COL, "Count", "Total", "Average"],
        )
        .interactive()
    )
else:
    chart_df = prov_summary
    bar = (
        alt.Chart(chart_df)
        .mark_bar()
        .encode(
            x=alt.X(f"{PROVINCE_COL}:N", sort="-y", title="Province"),
            y=alt.Y("count:Q", title="Count"),
            tooltip=[PROVINCE_COL, "count"],
        )
        .interactive()
    )

st.altair_chart(bar, use_container_width=True)

st.subheader("📌 District-level Chart")

if is_metric_numeric:
    dchart_df = dist_summary.rename(columns={"sum": "Total", "mean": "Average", "count": "Count"})
    dbar = (
        alt.Chart(dchart_df.head(30))
        .mark_bar()
        .encode(
            x=alt.X(f"{DISTRICT_COL}:N", sort="-y", title="District"),
            y=alt.Y("Total:Q", title=f"Top 30 Districts by Total {metric}"),
            tooltip=[PROVINCE_COL, DISTRICT_COL, "Count", "Total", "Average"],
        )
        .interactive()
    )
else:
    dchart_df = dist_summary
    dbar = (
        alt.Chart(dchart_df.head(30))
        .mark_bar()
        .encode(
            x=alt.X(f"{DISTRICT_COL}:N", sort="-y", title="District"),
            y=alt.Y("count:Q", title="Top 30 Districts by Count"),
            tooltip=[PROVINCE_COL, DISTRICT_COL, "count"],
        )
        .interactive()
    )

st.altair_chart(dbar, use_container_width=True)

st.divider()

# --- Tables ---
colA, colB = st.columns(2)

with colA:
    st.subheader("📄 Province Summary Table")
    st.dataframe(prov_summary, use_container_width=True, height=420)

with colB:
    st.subheader("📄 District Summary Table")
    st.dataframe(dist_summary, use_container_width=True, height=420)

st.divider()

# --- Download filtered data & summaries ---
st.subheader("⬇️ Downloads")

def to_csv_bytes(d: pd.DataFrame) -> bytes:
    return d.to_csv(index=False).encode("utf-8-sig")

d1, d2, d3 = st.columns(3)
with d1:
    st.download_button(
        "Download Filtered Data (CSV)",
        data=to_csv_bytes(fdf),
        file_name="filtered_data.csv",
        mime="text/csv",
    )
with d2:
    st.download_button(
        "Download Province Summary (CSV)",
        data=to_csv_bytes(prov_summary),
        file_name="province_summary.csv",
        mime="text/csv",
    )
with d3:
    st.download_button(
        "Download District Summary (CSV)",
        data=to_csv_bytes(dist_summary),
        file_name="district_summary.csv",
        mime="text/csv",
    )

st.caption("اگر نام ستون‌ها در شیت شما فرق دارد، فقط REGION_COL / PROVINCE_COL / DISTRICT_COL را مطابق شیت تنظیم کنید.")
