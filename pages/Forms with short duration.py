import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from io import BytesIO
import os

st.set_page_config(page_title="Pending Duration Check", layout="wide")
st.title("⏱ Pending Forms Duration Check")

qc_users = [
    "Waris Amini", "Shabeer Ahmad Ahsas", "Romal wali", "Abrahim Abrahimi",
    "Abdullah Deldar", "Hedayatullah Setanikzai", "A.Azim Hashimi",
    "Abed Ahmadzai", "Ahmad Akbari", "Inamullah Salamzai", "Hashmatullah Amarkhil",
    "Jalil Ahmad Jamal", "Khalid Ammar", "M.Samim Kohistani", "Meena Yawari",
    "Noryalai Hotak", "Sejadullah Safi", "Shahedullah Noorzad"
]

selected_users = st.multiselect("Select QC User(s):", qc_users)

SERVICE_ACCOUNT_FILE = r"C:\Users\LENOVO\CBE_Dashboard\service_account.json"
SPREADSHEET_URL = "https://docs.google.com/spreadsheets/d/1lkztBZ4eG1BQx-52XgnA6w8YIiw-Sm85pTlQQziurfw/edit"
SHEET_NAME = "QC_Log"

scope = ["https://www.googleapis.com/auth/spreadsheets"]
creds = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=scope)
client = gspread.authorize(creds)
sheet = client.open_by_url(SPREADSHEET_URL).worksheet(SHEET_NAME)

qc_data = pd.DataFrame(sheet.get_all_records())

base_path = r"C:\Users\LENOVO\Documents\DATA"
files = {
    "Tool 1": "Tool 1 CBE Classroom and Teacher_WIDE.xlsx",
    "Tool 7": "Tool 7 CBE Shura member Interview_WIDE.xlsx",
    "Tool 10": "Tool 10 Teacher Professional Training_WIDE.xlsx",
    "Tool 11": "Tool 11 – Public-School Principal Interview and Observation Checklist (School Infrastructure)_WIDE.xlsx"
}

if st.button("Check Pending Duration"):
    if not selected_users:
        st.warning("Please select at least one QC User.")
    else:
        all_results = []
        for tool_name, file_name in files.items():
            file_path = os.path.join(base_path, file_name)
            if os.path.exists(file_path):
                df_tool = pd.read_excel(file_path)

                expected_cols = ["KEY", "duration", "review_status"]
                if not all(col in df_tool.columns for col in expected_cols):
                    st.warning(f"Some expected columns missing in {tool_name}")
                    continue

                # فقط فرم‌های pending
                df_filtered = df_tool[df_tool["review_status"] == ""]

                # اضافه کردن نام QC
                df_filtered = df_filtered.merge(
                    qc_data[["KEY", "QC By"]],
                    on="KEY",
                    how="left"
                )

                # فیلتر کردن بر اساس کاربران انتخاب شده
                df_filtered = df_filtered[
                    df_filtered["QC By"].isin(selected_users) &
                    df_filtered["QC By"].notna()
                ]

                # تبدیل duration به دقیقه
                df_filtered["Change duration to minute"] = (df_filtered["duration"] / 60).round(2)

                # اعمال حداقل duration بر اساس تول
                if tool_name == "Tool 1":
                    min_duration = 20
                elif tool_name in ["Tool 7", "Tool 10"]:
                    min_duration = 15
                elif tool_name == "Tool 11":
                    min_duration = 30
                else:
                    min_duration = 0

                df_filtered = df_filtered[df_filtered["Change duration to minute"] >= min_duration]

                final_cols = ["KEY", "duration", "QC By", "Change duration to minute"]
                all_results.append(df_filtered[final_cols])
            else:
                st.error(f"File {file_name} not found!")

        if all_results:
            result_df = pd.concat(all_results, ignore_index=True)
            st.subheader("⏱ Pending Forms Duration Check Result")
            st.dataframe(result_df)

            buffer = BytesIO()
            result_df.to_excel(buffer, index=False)
            buffer.seek(0)
            st.download_button(
                label="Download Pending Duration Excel",
                data=buffer,
                file_name="Pending_Forms_Duration.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        else:
            st.info("No pending forms found for the selected QC User(s).")
