import streamlit as st
import pandas as pd
from io import BytesIO
import gspread
from google.oauth2.service_account import Credentials

st.set_page_config(page_title="CBE Correction Log", layout="wide")
st.title("Apply Correction Log to Uploaded File")

SPREADSHEET_URL = st.secrets.get("SPREADSHEET_URL", "")
CORRECTION_SHEET = st.secrets.get("CORRECTION_SHEET", "Correction_Log")

if not SPREADSHEET_URL:
    st.error("Missing SPREADSHEET_URL in Streamlit Secrets.")
    st.stop()

if "gcp_service_account" not in st.secrets:
    st.error("Missing gcp_service_account in Streamlit Secrets.")
    st.stop()

@st.cache_resource
def get_correction_sheet():
    scopes = ["https://www.googleapis.com/auth/spreadsheets.readonly"]
    creds = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=scopes
    )
    client = gspread.authorize(creds)
    return client.open_by_url(SPREADSHEET_URL).worksheet(CORRECTION_SHEET)

@st.cache_data(show_spinner=False)
def load_corrections():
    ws = get_correction_sheet()
    data = ws.get_all_records()
    return pd.DataFrame(data)

try:
    df_corrections = load_corrections()
except Exception as e:
    st.error(f"Failed to load Correction Log: {e}")
    st.stop()

uploaded_file = st.file_uploader("Upload your Excel file", type=["xlsx"])

if uploaded_file:
    try:
        all_sheets = pd.read_excel(uploaded_file, sheet_name=None, dtype=str)
    except Exception as e:
        st.error(f"Failed to read Excel file: {e}")
        st.stop()

    required_cols = {"Tool_Name", "Sheet_name", "KEY", "Question", "new_value"}
    missing = required_cols - set(df_corrections.columns)
    if missing:
        st.error(f"Correction_Log is missing required columns: {', '.join(sorted(missing))}")
        st.stop()

    tool_options = sorted(df_corrections["Tool_Name"].dropna().astype(str).unique().tolist())
    if not tool_options:
        st.error("No Tool_Name values found in Correction_Log.")
        st.stop()

    tool_name = st.selectbox("Select Tool Name matching this file:", tool_options)
    relevant_corrections = df_corrections[df_corrections["Tool_Name"].astype(str) == str(tool_name)].copy()

    if relevant_corrections.empty:
        st.warning("No corrections found for the selected tool.")
        st.stop()

    updated_sheets = {}
    total_changes = 0

    for sheet_name, df in all_sheets.items():
        df_updated = df.copy()

        if "KEY" not in df_updated.columns:
            updated_sheets[sheet_name] = df_updated
            continue

        sheet_corrections = relevant_corrections[
            relevant_corrections["Sheet_name"].astype(str) == str(sheet_name)
        ]

        if sheet_corrections.empty:
            updated_sheets[sheet_name] = df_updated
            continue

        applied_changes = 0

        for _, row in sheet_corrections.iterrows():
            key = "" if pd.isna(row["KEY"]) else str(row["KEY"])
            question = "" if pd.isna(row["Question"]) else str(row["Question"])
            new_value = "" if pd.isna(row["new_value"]) else str(row["new_value"])

            if not key or not question:
                continue

            if question in df_updated.columns:
                mask = df_updated["KEY"].astype(str) == key
                if mask.any():
                    df_updated.loc[mask, question] = new_value
                    applied_changes += int(mask.sum())

        total_changes += applied_changes
        updated_sheets[sheet_name] = df_updated

    st.success(f"Applied {total_changes} corrections.")

    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        for sname, sdf in updated_sheets.items():
            safe_name = str(sname)[:31] if sname else "Sheet1"
            sdf.to_excel(writer, sheet_name=safe_name, index=False)

    buffer.seek(0)

    st.download_button(
        label="Download Corrected File",
        data=buffer,
        file_name=uploaded_file.name.replace(".xlsx", "_Corrected.xlsx"),
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
