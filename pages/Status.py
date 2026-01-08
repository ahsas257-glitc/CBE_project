import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from io import BytesIO
import os

st.set_page_config(page_title="CBE Dashboard Updater", layout="wide")

# Sidebar for page selection
page = st.sidebar.selectbox("Select Page", ["Updater", "Status"])

SERVICE_ACCOUNT_FILE = r"C:\Users\LENOVO\CBE_Dashboard\service_account.json"
SPREADSHEET_URL = "https://docs.google.com/spreadsheets/d/1lkztBZ4eG1BQx-52XgnA6w8YIiw-Sm85pTlQQziurfw/edit?gid=742958808#gid=742958808"
SHEET_NAME = "QC_Log"

scope = ["https://www.googleapis.com/auth/spreadsheets"]
creds = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=scope)
client = gspread.authorize(creds)
sheet = client.open_by_url(SPREADSHEET_URL).worksheet(SHEET_NAME)

data = sheet.get_all_records()
df_qc = pd.DataFrame(data)

base_path = r"C:\Users\LENOVO\Documents\DATA"
files = {
    "Tool 1": "Tool 1 CBE Classroom and Teacher.xlsx",
    "Tool 7": "Tool 7 CBE Shura member Interview.xlsx",
    "Tool 10": "Tool 10 Teacher Professional Training.xlsx",
    "Tool 11": "Tool 11 – Public-School Principal Interview and Observation Checklist (School Infrastructure).xlsx"
}

if page == "Updater":
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
        1. Upload the Excel files (**Tool 1, 7, 10, 11**) OR use the default file path.  
        2. The system will automatically read, merge, and compare the new data with the existing records in **QC_Log**.  
        3. New keys (**unique records**) will be highlighted in a preview table.  
        4. You can:  
            - **Download** the new keys as an Excel file.  
            - **Directly add** them into the Google Sheet (**QC_Log Dashboard**) by clicking the button.  

        ✅ Please note:  
        This page is **only for updating data**. Avoid making manual edits directly inside **QC_Log**, as this may cause inconsistencies.  
        """
    )
    st.divider()

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
                if file:
                    df = pd.read_excel(file)
                else:
                    df = pd.read_excel(os.path.join(base_path, file_name))
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

        existing_keys = set(df_qc["KEY"].astype(str).tolist())
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
                new_rows = new_rows.fillna("").astype(str)
                new_values = new_rows.values.tolist()
                sheet.append_rows(new_values, value_input_option="RAW")
                st.success("✅ New rows successfully added to QC_Log.")
        else:
            st.success("✅ All keys already exist in QC_Log.")

elif page == "Status":
    st.title("CBE Dashboard Status Checker")
    st.markdown(
        """
        This page checks the status between the Google Sheet (QC_Log) and the review_status in the monitoring tools.

        ### 📝 Instructions:
        1. Upload the Excel files (**Tool 1, 7, 10, 11**) OR use the default file path.  
        2. The system will compare 'Status' from QC_Log with 'review_status' from the tools.  
        3. A preview table will show the comparison results.  
        4. You can download the results as an Excel file.
        """
    )
    st.divider()

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
                if file:
                    df = pd.read_excel(file)
                else:
                    df = pd.read_excel(os.path.join(base_path, file_name))
            else:
                df = pd.read_excel(os.path.join(base_path, file_name))

            temp_df = pd.DataFrame({
                "KEY": df.get("KEY", "").astype(str),
                "Tool Name": tool_name,
                "DS_Status": df.get("review_status", pd.Series([""] * len(df))).fillna("").astype(str),
                "QA_By": df.get("QA_By", pd.Series([""] * len(df))).fillna("").astype(str),
                "QA_status": df.get("QA_status", pd.Series([""] * len(df))).fillna("").astype(str)
            })

            merged_data.append(temp_df)

        final_df = pd.concat(merged_data, ignore_index=True).drop_duplicates(subset=["KEY"])

        # Get Status and QC By from QC_Log
        df_qc_status = df_qc[["KEY", "Status", "QC By"]].copy()
        df_qc_status["KEY"] = df_qc_status["KEY"].astype(str)
        df_qc_status["GS_Status"] = df_qc_status["Status"].fillna("").astype(str)
        df_qc_status["QC By"] = df_qc_status["QC By"].fillna("").astype(str)
        df_qc_status = df_qc_status.drop(columns=["Status"])

        # Merge on KEY
        comparison_df = final_df.merge(df_qc_status, on="KEY", how="left").fillna({"GS_Status": "", "QC By": ""})

        # Select output columns
        output_df = comparison_df[["KEY", "Tool Name", "QC By", "GS_Status", "DS_Status", "QA_By", "QA_status"]]

        st.subheader("📊 Status Comparison")
        st.dataframe(output_df)

        if not output_df.empty:
            buffer = BytesIO()
            output_df.to_excel(buffer, index=False)
            buffer.seek(0)
            st.download_button(
                label="Download Status Report",
                data=buffer,
                file_name="status_comparison.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        else:
            st.info("No data to compare.")