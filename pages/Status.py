import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from io import BytesIO

st.set_page_config(page_title="CBE Dashboard Updater", layout="wide")

page = st.sidebar.selectbox("Select Page", ["Updater", "Status"])

SPREADSHEET_URL = "https://docs.google.com/spreadsheets/d/1lkztBZ4eG1BQx-52XgnA6w8YIiw-Sm85pTlQQziurfw/edit?gid=742958808#gid=742958808"
SHEET_NAME = "QC_Log"

scope = ["https://www.googleapis.com/auth/spreadsheets"]
creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scope)
client = gspread.authorize(creds)
sheet = client.open_by_url(SPREADSHEET_URL).worksheet(SHEET_NAME)

df_qc = pd.DataFrame(sheet.get_all_records())
if not df_qc.empty and "KEY" in df_qc.columns:
    df_qc["KEY"] = df_qc["KEY"].astype(str)

files = {
    "Tool 1": "Tool 1 CBE Classroom and Teacher.xlsx",
    "Tool 7": "Tool 7 CBE Shura member Interview.xlsx",
    "Tool 10": "Tool 10 Teacher Professional Training.xlsx",
    "Tool 11": "Tool 11 – Public-School Principal Interview and Observation Checklist (School Infrastructure).xlsx"
}

st.subheader("Upload Excel files (Tool 1, 7, 10, 11)")
uploaded_files = st.file_uploader("Upload all required files", type=["xlsx"], accept_multiple_files=True)

uploaded_map = {f.name: f for f in uploaded_files} if uploaded_files else {}
missing = [name for name in files.values() if name not in uploaded_map]

if missing:
    st.warning("Missing required files:")
    st.write(missing)
    st.stop()

def read_tool_df(tool_name, file_obj):
    df = pd.read_excel(file_obj)
    if "KEY" in df.columns:
        df["KEY"] = df["KEY"].astype(str)
    if tool_name in ["Tool 1", "Tool 7"]:
        cbe_school_name = df.get("NAME_OF_THE_CBE", pd.Series([""] * len(df)))
        tpm_id = df.get("TPM_CBE_ID", pd.Series([""] * len(df)))
    else:
        cbe_school_name = df.get("School_name_in_English", pd.Series([""] * len(df)))
        tpm_id = df.get("TPM_ID", pd.Series([""] * len(df)))
    survey_date = pd.to_datetime(df.get("starttime", pd.NaT), errors="coerce").dt.strftime("%Y-%m-%d")
    out = pd.DataFrame({
        "KEY": df.get("KEY", pd.Series([""] * len(df))).astype(str),
        "Tool Name": tool_name,
        "Province": df.get("Province", pd.Series([""] * len(df))).fillna("").astype(str),
        "District": df.get("District", pd.Series([""] * len(df))).fillna("").astype(str),
        "Village": df.get("Village", pd.Series([""] * len(df))).fillna("").astype(str),
        "CBE/School Name": cbe_school_name.fillna("").astype(str),
        "TPM CBE/School ID": tpm_id.fillna("").astype(str),
        "Surveyor Name": df.get("Surveyor_Name", pd.Series([""] * len(df))).fillna("").astype(str),
        "Surveyor ID": df.get("Surveyor_Id", pd.Series([""] * len(df))).fillna("").astype(str),
        "Survey_Date": survey_date.fillna("").astype(str)
    })
    return out

def build_merged_tools():
    merged = []
    for tool_name, file_name in files.items():
        merged.append(read_tool_df(tool_name, uploaded_map[file_name]))
    final_columns = [
        "KEY", "Tool Name", "Province", "District", "Village",
        "CBE/School Name", "TPM CBE/School ID",
        "Surveyor Name", "Surveyor ID", "Survey_Date"
    ]
    return pd.concat(merged, ignore_index=True)[final_columns]

if page == "Updater":
    st.title("CBE Dashboard Updater")
    st.markdown(
        """
        This tool updates QC_Log using Tool 1, Tool 7, Tool 10, and Tool 11 files.
        Upload all required files, review the new keys, then download or append them to QC_Log.
        """
    )
    st.divider()

    final_df = build_merged_tools()

    if df_qc.empty or "KEY" not in df_qc.columns:
        existing_keys = set()
    else:
        existing_keys = set(df_qc["KEY"].astype(str).tolist())

    new_rows = final_df[~final_df["KEY"].astype(str).isin(existing_keys)]

    st.subheader("New Keys")
    st.dataframe(new_rows, use_container_width=True)

    if new_rows.empty:
        st.success("All keys already exist in QC_Log.")
        st.stop()

    buffer = BytesIO()
    new_rows.to_excel(buffer, index=False)
    buffer.seek(0)

    st.download_button(
        label="Download New Keys",
        data=buffer,
        file_name="new_keys.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    if st.button("Add to QC_Log"):
        new_rows_clean = new_rows.fillna("").astype(str)
        sheet.append_rows(new_rows_clean.values.tolist(), value_input_option="RAW")
        st.success("New rows added to QC_Log successfully.")

elif page == "Status":
    st.title("CBE Dashboard Status Checker")
    st.markdown(
        """
        This page compares Status in QC_Log with review_status in the monitoring tools.
        Upload all required files to generate the comparison report.
        """
    )
    st.divider()

    merged = []
    for tool_name, file_name in files.items():
        df = pd.read_excel(uploaded_map[file_name], dtype=str)
        if "KEY" in df.columns:
            df["KEY"] = df["KEY"].astype(str)
        merged.append(pd.DataFrame({
            "KEY": df.get("KEY", pd.Series([""] * len(df))).astype(str),
            "Tool Name": tool_name,
            "DS_Status": df.get("review_status", pd.Series([""] * len(df))).fillna("").astype(str),
            "QA_By": df.get("QA_By", pd.Series([""] * len(df))).fillna("").astype(str),
            "QA_status": df.get("QA_status", pd.Series([""] * len(df))).fillna("").astype(str),
        }))

    final_df = pd.concat(merged, ignore_index=True).drop_duplicates(subset=["KEY"])

    if df_qc.empty:
        df_qc_status = pd.DataFrame(columns=["KEY", "QC By", "GS_Status"])
    else:
        needed = ["KEY", "Status", "QC By"]
        for c in needed:
            if c not in df_qc.columns:
                df_qc[c] = ""
        df_qc_status = df_qc[["KEY", "Status", "QC By"]].copy()
        df_qc_status["KEY"] = df_qc_status["KEY"].astype(str)
        df_qc_status["GS_Status"] = df_qc_status["Status"].fillna("").astype(str)
        df_qc_status["QC By"] = df_qc_status["QC By"].fillna("").astype(str)
        df_qc_status = df_qc_status.drop(columns=["Status"])

    comparison_df = final_df.merge(df_qc_status, on="KEY", how="left").fillna({"GS_Status": "", "QC By": ""})
    output_df = comparison_df[["KEY", "Tool Name", "QC By", "GS_Status", "DS_Status", "QA_By", "QA_status"]]

    st.subheader("Status Comparison")
    st.dataframe(output_df, use_container_width=True)

    buffer = BytesIO()
    output_df.to_excel(buffer, index=False)
    buffer.seek(0)

    st.download_button(
        label="Download Status Report",
        data=buffer,
        file_name="status_comparison.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
