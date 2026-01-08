import streamlit as st
import pandas as pd
from io import BytesIO
import gspread
from google.oauth2.service_account import Credentials

st.set_page_config(page_title="CBE Correction Log", layout="wide")
st.title("🛠️ Apply Correction Log to Uploaded File")

SERVICE_ACCOUNT_FILE = r"C:\Users\LENOVO\CBE_Dashboard\service_account.json"
SPREADSHEET_KEY = "1lkztBZ4eG1BQx-52XgnA6w8YIiw-Sm85pTlQQziurfw"
CORRECTION_SHEET = "Correction_Log"

def load_corrections():
    scopes = ["https://www.googleapis.com/auth/spreadsheets.readonly"]
    creds = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=scopes)
    client = gspread.authorize(creds)
    sheet = client.open_by_key(SPREADSHEET_KEY).worksheet(CORRECTION_SHEET)
    data = sheet.get_all_records()
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

    tool_name = st.selectbox(
        "Select Tool Name matching this file:",
        df_corrections["Tool_Name"].unique()
    )

    relevant_corrections = df_corrections[df_corrections["Tool_Name"] == tool_name]

    updated_sheets = {}
    total_changes = 0

    for sheet_name, df in all_sheets.items():
        df_updated = df.copy()
        applied_changes = 0

        sheet_corrections = relevant_corrections[relevant_corrections["Sheet_name"] == sheet_name]

        for _, row in sheet_corrections.iterrows():
            key = str(row["KEY"])
            question = row["Question"]
            new_value = str(row["new_value"])

            if question in df_updated.columns:
                mask = df_updated["KEY"].astype(str) == key
                if mask.any():
                    df_updated.loc[mask, question] = new_value
                    applied_changes += 1

        total_changes += applied_changes
        updated_sheets[sheet_name] = df_updated

    st.success(f"✅ Applied {total_changes} corrections across relevant sheets.")

    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        for sheet_name, df in updated_sheets.items():
            df.to_excel(writer, sheet_name=sheet_name, index=False)
    buffer.seek(0)

    st.download_button(
        label=f"⬇️ Download Corrected File",
        data=buffer,
        file_name=uploaded_file.name.replace(".xlsx", "_Corrected.xlsx"),
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
