import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from io import BytesIO

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
    - Upload the Excel files (**Tool 1, 7, 10, 11**).
    - The system will read, merge, and compare with **QC_Log**.
    - New keys will be shown and can be downloaded or pushed to Google Sheet.

    ✅ Please note:  
    This page is **only for updating data**. Avoid manual edits in **QC_Log**.
    """
)
st.divider()

# ---------- CONFIG (Cloud-friendly) ----------
# Put these in Streamlit Cloud Secrets (explained below):
# st.secrets["gcp_service_account"]  -> service account JSON as dict
# st.secrets["SPREADSHEET_URL"]      -> your sheet URL
# st.secrets["SHEET_NAME"]           -> QC_Log (optional; default QC_Log)

SPREADSHEET_URL = st.secrets["SPREADSHEET_URL"]
SHEET_NAME = st.secrets.get("SHEET_NAME", "QC_Log")

scope = ["https://www.googleapis.com/auth/spreadsheets"]

@st.cache_resource
def get_sheet():
    creds = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=scope
    )
    client = gspread.authorize(creds)
    ws = client.open_by_url(SPREADSHEET_URL).worksheet(SHEET_NAME)
    return ws

sheet = get_sheet()

@st.cache_data(show_spinner=False)
def load_qc_log():
    data = sheet.get_all_records()
    return pd.DataFrame(data)

df_qc = load_qc_log()

files_map = {
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
    "Upload all 4 files (names can match, but best if they match the expected file names)",
    type=["xlsx"],
    accept_multiple_files=True
)

def find_uploaded_file(expected_name: str):
    # Match by exact filename first; if not found, return None
    for f in uploaded_files:
        if f.name == expected_name:
            return f
    return None

def safe_col(df, colname, default=""):
    return df[colname] if colname in df.columns else default

if uploaded_files:
    merged_data = []

    for tool_name, expected_filename in files_map.items():
        up = find_uploaded_file(expected_filename)
        if up is None:
            st.error(f"فایل مربوط به {tool_name} را پیدا نکردم. لطفاً دقیقاً همین نام را آپلود کن: {expected_filename}")
            st.stop()

        df = pd.read_excel(up)

        if tool_name in ["Tool 1", "Tool 7"]:
            cbe_school_name = safe_col(df, "NAME_OF_THE_CBE", "")
            tpm_id = safe_col(df, "TPM_CBE_ID", "")
        else:
            cbe_school_name = safe_col(df, "School_name_in_English", "")
            tpm_id = safe_col(df, "TPM_ID", "")

        survey_date = pd.to_datetime(safe_col(df, "starttime", pd.NaT), errors="coerce")
        survey_date = survey_date.dt.strftime("%Y-%m-%d")

        temp_df = pd.DataFrame({
            "KEY": safe_col(df, "KEY", ""),
            "Tool Name": tool_name,
            "Province": safe_col(df, "Province", ""),
            "District": safe_col(df, "District", ""),
            "Village": safe_col(df, "Village", ""),
            "CBE/School Name": cbe_school_name,
            "TPM CBE/School ID": tpm_id,
            "Surveyor Name": safe_col(df, "Surveyor_Name", ""),
            "Surveyor ID": safe_col(df, "Surveyor_Id", ""),
            "Survey_Date": survey_date
        })

        merged_data.append(temp_df)

    final_df = pd.concat(merged_data, ignore_index=True)

    # Ensure columns exist
    for col in final_columns:
        if col not in final_df.columns:
            final_df[col] = ""

    final_df = final_df[final_columns]

    if "KEY" not in df_qc.columns:
        st.warning("در QC_Log ستون KEY پیدا نشد. لطفاً مطمئن شو که در شیت QC_Log ستون KEY موجود است.")
        st.stop()

    existing_keys = set(df_qc["KEY"].astype(str).fillna("").tolist())
    new_rows = final_df[~final_df["KEY"].astype(str).fillna("").isin(existing_keys)]

    st.subheader("🔑 New Keys")
    st.dataframe(new_rows, use_container_width=True)

    if not new_rows.empty:
        buffer = BytesIO()
        new_rows.to_excel(buffer, index=False)
        buffer.seek(0)

        st.download_button(
            label="⬇️ Download new keys (Excel)",
            data=buffer,
            file_name="new_keys.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

        if st.button("✅ Add in Dashboard (Append to QC_Log)"):
            new_rows_clean = new_rows.fillna("").astype(str)
            new_values = new_rows_clean.values.tolist()

            sheet.append_rows(new_values, value_input_option="RAW")
            st.success("✅ New rows successfully added to QC_Log.")

            # refresh cached QC log
            load_qc_log.clear()
    else:
        st.success("✅ All keys already exist in QC_Log.")

else:
    st.info("لطفاً ۴ فایل Tool را آپلود کن تا سیستم مقایسه و آپدیت را انجام دهد.")
