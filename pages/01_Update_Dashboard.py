import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from io import BytesIO
import os

st.set_page_config(page_title="CBE Dashboard Updater", layout="wide")
st.title("CBE Dashboard Updater")

st.markdown(
    """
    This application has been developed under the **UNICEF CBE Project** as part of 
    the **Third Party Monitoring (TPM) work by PPC**.  
    The purpose of this tool is to **simplify and automate the process of updating 
    the QC_Log dashboard** with data collected through monitoring tools.

    ### 📂 Required Monitoring Tools:
    - Tool 1: *CBE Classroom and Teacher*  
    - Tool 7: *CBE Shura Member Interview*  
    - Tool 10: *Teacher Professional Training*  
    - Tool 11: *Public-School Principal Interview & Observation Checklist*  

    ### 📝 Instructions:
    - Upload the Excel files (**Tool 1, 7, 10, 11**) OR use the default file path.  
    - The system reads/merges data and compares with **QC_Log**.  
    - New keys will show in a preview table.  
    - You can download new keys or push them to Google Sheet.

    ✅ Avoid manual edits in QC_Log.
    """
)
st.divider()

# -----------------------------
# HARD-CODED SETTINGS (as you requested)
# -----------------------------
SPREADSHEET_URL = "https://docs.google.com/spreadsheets/d/1lkztBZ4eG1BQx-52XgnA6w8YIiw-Sm85pTlQQziurfw/edit"
SHEET_NAME = "QC_Log"  # worksheet/tab name in the spreadsheet

# -----------------------------
# AUTH: read ONLY from secrets (no local path)
# -----------------------------
scope = ["https://www.googleapis.com/auth/spreadsheets"]
service_account_info = st.secrets["gcp_service_account"]

creds = Credentials.from_service_account_info(service_account_info, scopes=scope)
client = gspread.authorize(creds)

# Open sheet
sheet = client.open_by_url(SPREADSHEET_URL).worksheet(SHEET_NAME)

# Read existing QC_Log data
data = sheet.get_all_records()
df_qc = pd.DataFrame(data)

# -----------------------------
# Local default path (optional)
# On Streamlit Cloud, this path won't exist. It's okay; upload will be used.
# -----------------------------
base_path = r"C:\Users\LENOVO\Documents\DATA"

files = {
    "Tool 1": "Tool 1 CBE Classroom and Teacher.xlsx",
    "Tool 7": "Tool 7 CBE Shura member Interview.xlsx",
    "Tool 10": "Tool 10 Teacher Professional Training.xlsx",
    "Tool 11": "Tool 11 – Public-School Principal Interview and Observation Checklist (School Infrastructure).xlsx"
}

final_columns = [
    "KEY", "Tool Name", "Province", "District", "Village",
    "CBE/School Name", "TPM CBE/School ID",
    "Surveyor Name", "Surveyor ID", "Survey_Date"
]

st.subheader("📥 Upload Excel files (Tool 1, 7, 10, 11)")
uploaded_files = st.file_uploader(
    "Upload the required Excel files (or use default path if running locally)",
    type=["xlsx"],
    accept_multiple_files=True
)

def read_tool_file(tool_name: str, file_name: str, uploaded_files, base_path: str) -> pd.DataFrame:
    """
    Priority:
    1) If uploaded file with exact name exists -> read it
    2) Else try local path (for local runs)
    """
    if uploaded_files:
        f = next((x for x in uploaded_files if x.name == file_name), None)
        if f is not None:
            return pd.read_excel(f)

    local_fp = os.path.join(base_path, file_name)
    if os.path.exists(local_fp):
        return pd.read_excel(local_fp)

    # If not found, return empty df
    return pd.DataFrame()

if uploaded_files or all(os.path.exists(os.path.join(base_path, f)) for f in files.values()):
    merged_data = []

    for tool_name, file_name in files.items():
        df = read_tool_file(tool_name, file_name, uploaded_files, base_path)

        if df.empty:
            st.warning(f"⚠️ File not found or empty for: {tool_name} ({file_name})")
            continue

        # Tool-specific columns
        if tool_name in ["Tool 1", "Tool 7"]:
            cbe_school_name = df.get("NAME_OF_THE_CBE", "")
            tpm_id = df.get("TPM_CBE_ID", "")
        else:
            cbe_school_name = df.get("School_name_in_English", "")
            tpm_id = df.get("TPM_ID", "")

        survey_date = pd.to_datetime(df.get("starttime", pd.NaT), errors="coerce").dt.strftime("%Y-%m-%d")

        temp_df = pd.DataFrame({
            "KEY": df.get("KEY", ""),
            "Tool Name": tool_name,
            "Province": df.get("Province", ""),
            "District": df.get("District", ""),
            "Village": df.get("Village", ""),
            "CBE/School Name": cbe_school_name,
            "TPM CBE/School ID": tpm_id,
            "Surveyor Name": df.get("Surveyor_Name", ""),
            "Surveyor ID": df.get("Surveyor_Id", ""),
            "Survey_Date": survey_date
        })

        merged_data.append(temp_df)

    if not merged_data:
        st.error("No valid tool files loaded. Please upload the Excel files.")
        st.stop()

    final_df = pd.concat(merged_data, ignore_index=True)

    # Ensure all required columns exist
    for c in final_columns:
        if c not in final_df.columns:
            final_df[c] = ""

    final_df = final_df[final_columns]

    # Compare keys
    if "KEY" not in df_qc.columns:
        st.error("QC_Log sheet does not contain a 'KEY' column.")
        st.stop()

    existing_keys = set(df_qc["KEY"].astype(str).tolist())
    new_rows = final_df[~final_df["KEY"].astype(str).isin(existing_keys)]

    st.subheader("🔑 New Keys")
    st.dataframe(new_rows, use_container_width=True)

    if not new_rows.empty:
        buffer = BytesIO()
        new_rows.to_excel(buffer, index=False)
        buffer.seek(0)

        st.download_button(
            label="Download New Keys (Excel)",
            data=buffer,
            file_name="new_keys.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

        if st.button("Add in Dashboard"):
            new_rows_clean = new_rows.fillna("").astype(str)
            new_values = new_rows_clean.values.tolist()
            sheet.append_rows(new_values, value_input_option="RAW")
            st.success("✅ New rows successfully added to QC_Log.")
    else:
        st.success("✅ All keys already exist in QC_Log.")
else:
    st.info("Please upload the Excel files (Tool 1, 7, 10, 11).")
