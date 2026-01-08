import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from io import BytesIO
import os
from theme.theme import apply_theme, asset_path

st.set_page_config(page_title="CBE Dashboard Updater", layout="wide")
st.title("CBE Dashboard Updater")

st.markdown(
    """
    This application has been developed under the **UNICEF CBE Project** as part of 
    the **Third Party Monitoring (TPM) work by PPC**.  
    The purpose of this tool is to **simplify and automate the process of updating 
    the QC_Log dashboard** with data collected through monitoring tools.
    """
)
st.divider()

# ✅ (ثابت داخل کد)
SPREADSHEET_URL = "https://docs.google.com/spreadsheets/d/1lkztBZ4eG1BQx-52XgnA6w8YIiw-Sm85pTlQQziurfw/edit?gid=742958808#gid=742958808"
SHEET_NAME = "QC_Log"

# ✅ فقط Credential از Secrets خوانده می‌شود (بدون فایل json لوکال)
# در secrets.toml باید یک دیکشنری به نام gcp_service_account داشته باشید
scope = ["https://www.googleapis.com/auth/spreadsheets"]
creds = Credentials.from_service_account_info(
    st.secrets["gcp_service_account"],
    scopes=scope
)
client = gspread.authorize(creds)
sheet = client.open_by_url(SPREADSHEET_URL).worksheet(SHEET_NAME)

# خواندن دیتای فعلی QC_Log
data = sheet.get_all_records()
df_qc = pd.DataFrame(data)

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
    "Or use default path",
    type=["xlsx"],
    accept_multiple_files=True
)

if uploaded_files or all(os.path.exists(os.path.join(base_path, f)) for f in files.values()):
    merged_data = []

    for tool_name, file_name in files.items():
        if uploaded_files:
            file = next((f for f in uploaded_files if f.name == file_name), None)
            df = pd.read_excel(file) if file else pd.read_excel(os.path.join(base_path, file_name))
        else:
            df = pd.read_excel(os.path.join(base_path, file_name))

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

    final_df = pd.concat(merged_data, ignore_index=True)[final_columns]

    existing_keys = set(df_qc.get("KEY", pd.Series([], dtype=str)).astype(str).tolist())
    new_rows = final_df[~final_df["KEY"].astype(str).isin(existing_keys)]

    st.subheader("🔑 New Keys")
    st.dataframe(new_rows)

    if not new_rows.empty:
        buffer = BytesIO()
        new_rows.to_excel(buffer, index=False)
        buffer.seek(0)

        st.download_button(
            label="Download",
            data=buffer,
            file_name="new_keys.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

        if st.button("Add in Dashboard"):
            new_rows_clean = new_rows.fillna("").astype(str)
            sheet.append_rows(new_rows_clean.values.tolist(), value_input_option="RAW")
            st.success("✅ New rows successfully added to QC_Log.")
    else:
        st.success("✅ All keys already exist in QC_Log.")
