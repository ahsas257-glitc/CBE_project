import os
from io import BytesIO

import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials


def load_css(path="theme/styles.css"):
    # اگر فایل نبود، اپ کرش نکند
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)


@st.cache_resource(show_spinner=False)
def get_gsheet_client():
    """
    Streamlit Cloud:
    Service Account را از st.secrets می‌خوانیم (نه از C:\\...).
    باید در .streamlit/secrets.toml قرار داده شود.
    """
    scope = ["https://www.googleapis.com/auth/spreadsheets"]

    # روش پیشنهادی: کل JSON سرویس اکانت داخل secrets با کلید gcp_service_account
    # مثل: st.secrets["gcp_service_account"]["client_email"] ...
    service_info = st.secrets["gcp_service_account"]
    creds = Credentials.from_service_account_info(service_info, scopes=scope)
    return gspread.authorize(creds)


@st.cache_data(show_spinner=False)
def get_qc_log_dataframe(spreadsheet_url: str, sheet_name: str) -> pd.DataFrame:
    client = get_gsheet_client()
    ws = client.open_by_url(spreadsheet_url).worksheet(sheet_name)
    data = ws.get_all_records()
    return pd.DataFrame(data)


def read_tool_file(uploaded_files, base_path, file_name) -> pd.DataFrame:
    """
    اگر فایل آپلود شد همان را بخوان، اگر نه و base_path داده شد از روی مسیر پروژه بخوان.
    در Streamlit Cloud معمولاً بهتر است فقط Upload داشته باشی.
    """
    if uploaded_files:
        f = next((x for x in uploaded_files if x.name == file_name), None)
        if f is not None:
            return pd.read_excel(f)

    if base_path:
        local_path = os.path.join(base_path, file_name)
        if os.path.exists(local_path):
            return pd.read_excel(local_path)

    # اگر هیچ کدام نبود، خطا بده تا کاربر بفهمد کدام فایل کم است
    raise FileNotFoundError(f"File not provided: {file_name}")


def main():
    st.set_page_config(page_title="CBE Dashboard Updater", layout="wide")
    load_css()

    st.markdown(
        """
        <div class="glass" style="position:relative;">
          <div style="font-size:28px; font-weight:850;">CBE Dashboard Updater</div>
          <div class="small-muted" style="margin-top:6px;">
            UNICEF CBE Project • Third Party Monitoring (TPM) by PPC
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        """
        This application has been developed under the **UNICEF CBE Project** as part of 
        the **Third Party Monitoring (TPM) work by PPC**.  
        The purpose of this tool is to **simplify and automate the process of updating 
        the QC_Log dashboard** with data collected through monitoring tools.

        **Required Monitoring Tools**
        - Tool 1: *CBE Classroom and Teacher*  
        - Tool 7: *CBE Shura Member Interview*  
        - Tool 10: *Teacher Professional Training*  
        - Tool 11: *Public-School Principal Interview & Observation Checklist*  
        """,
    )
    st.divider()

    # تنظیمات Google Sheet
    SPREADSHEET_URL = st.secrets.get(
        "spreadsheet_url",
        "https://docs.google.com/spreadsheets/d/1lkztBZ4eG1BQx-52XgnA6w8YIiw-Sm85pTlQQziurfw/edit"
    )
    SHEET_NAME = st.secrets.get("sheet_name", "QC_Log")

    # در Cloud بهتر است base_path خالی باشد (فقط Upload)
    # اگر Local می‌خواهی استفاده کنی، base_path را اینجا بده
    base_path = ""  # مثال لوکال: r"D:\DATA"

    files = {
        "Tool 1": "Tool 1 CBE Classroom and Teacher.xlsx",
        "Tool 7": "Tool 7 CBE Shura member Interview.xlsx",
        "Tool 10": "Tool 10 Teacher Professional Training.xlsx",
        "Tool 11": "Tool 11 – Public-School Principal Interview and Observation Checklist (School Infrastructure).xlsx",
    }

    final_columns = [
        "KEY", "Tool Name", "Province", "District", "Village",
        "CBE/School Name", "TPM CBE/School ID",
        "Surveyor Name", "Surveyor ID", "Survey_Date"
    ]

    st.subheader("📥 Upload Excel files (Tool 1, 7, 10, 11)")
    uploaded_files = st.file_uploader(
        "Upload the exact files (same names) or rename accordingly",
        type=["xlsx"],
        accept_multiple_files=True
    )

    # خواندن QC_Log
    try:
        df_qc = get_qc_log_dataframe(SPREADSHEET_URL, SHEET_NAME)
        if df_qc.empty:
            st.warning("QC_Log sheet is empty or could not be read properly.")
    except Exception as e:
        st.error("Could not connect/read QC_Log from Google Sheet.")
        st.exception(e)
        return

    # اگر کلید KEY در QC_Log نبود
    if "KEY" not in df_qc.columns:
        st.error("QC_Log does not contain a 'KEY' column. Please verify the sheet structure.")
        return

    can_proceed = bool(uploaded_files) or (
        bool(base_path) and all(os.path.exists(os.path.join(base_path, f)) for f in files.values())
    )

    if not can_proceed:
        st.info("Please upload the required Excel files.")
        return

    merged_data = []

    for tool_name, file_name in files.items():
        try:
            df = read_tool_file(uploaded_files, base_path, file_name)
        except Exception as e:
            st.error(f"Missing/invalid file for {tool_name}: {file_name}")
            st.exception(e)
            return

        # ستون‌های متفاوت Tool 1/7 vs Tool 10/11
        if tool_name in ["Tool 1", "Tool 7"]:
            cbe_school_name = df.get("NAME_OF_THE_CBE", "")
            tpm_id = df.get("TPM_CBE_ID", "")
        else:
            cbe_school_name = df.get("School_name_in_English", "")
            tpm_id = df.get("TPM_ID", "")

        # تاریخ
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

    final_df = pd.concat(merged_data, ignore_index=True)

    # تضمین ستون‌ها
    for col in final_columns:
        if col not in final_df.columns:
            final_df[col] = ""

    final_df = final_df[final_columns]

    existing_keys = set(df_qc["KEY"].astype(str).fillna("").tolist())
    new_rows = final_df[~final_df["KEY"].astype(str).fillna("").isin(existing_keys)]

    st.subheader("🔑 New Keys (Not in QC_Log)")
    st.dataframe(new_rows, use_container_width=True)

    if new_rows.empty:
        st.success("✅ All keys already exist in QC_Log.")
        return

    # دانلود اکسل
    buffer = BytesIO()
    new_rows.to_excel(buffer, index=False)
    buffer.seek(0)

    st.download_button(
        label="Download new keys (Excel)",
        data=buffer,
        file_name="new_keys.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    # اضافه کردن به شیت
    if st.button("Add in Dashboard"):
        try:
            client = get_gsheet_client()
            ws = client.open_by_url(SPREADSHEET_URL).worksheet(SHEET_NAME)

            safe_rows = new_rows.fillna("").astype(str)
            ws.append_rows(safe_rows.values.tolist(), value_input_option="RAW")

            st.success("✅ New rows successfully added to QC_Log.")
            # برای به‌روز شدن کش
            st.cache_data.clear()
        except Exception as e:
            st.error("Failed to append rows to QC_Log.")
            st.exception(e)


if __name__ == "__main__":
    main()
