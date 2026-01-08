import pandas as pd
import streamlit as st
from io import BytesIO
import gspread
from google.oauth2.service_account import Credentials

st.set_page_config(page_title="Tool 10 QC Issues", layout="wide")
st.title("🛠 Tool 10 QC Issues")

SERVICE_ACCOUNT_FILE = r"C:\Users\LENOVO\CBE_Dashboard\service_account.json"
SPREADSHEET_URL = "https://docs.google.com/spreadsheets/d/1lkztBZ4eG1BQx-52XgnA6w8YIiw-Sm85pTlQQziurfw/edit"
SHEET_NAME = "QC_Log"

def load_qc_log():
    scopes = ["https://www.googleapis.com/auth/spreadsheets.readonly"]
    creds = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=scopes)
    client = gspread.authorize(creds)
    sheet = client.open_by_url(SPREADSHEET_URL).worksheet(SHEET_NAME)
    data = sheet.get_all_records()
    df = pd.DataFrame(data)
    df.columns = df.columns.str.strip()
    df["KEY"] = df["KEY"].astype(str).str.strip()
    df["QC By"] = df["QC By"].astype(str).str.strip()
    return df

users = ["All",
         "Waris Amini", "Shabeer Ahmad Ahsas", "Romal wali",
         "Abrahim Ahrahimi", "Abdullah Deldar", "Hedayatullah Setanikzai",
         "A.Azim Hashimi", "Abed Ahmadzai", "Ahmad Akbari",
         "Inamullah Salamzai", "Hashmatullah Amarkhil", "Jalil Ahmad Jamal",
         "Khalid Ammar", "M.Samim Kohistani", "Meena Yawari",
         "Noryalai Hotak", "Sejadullah Safi", "Shahedullah Noorzad"]
selected_user = st.selectbox("Select your name", users)

tool_file = st.file_uploader("Upload Tool 10 Excel File", type=["xlsx"])

if tool_file:
    try:
        df_tool = pd.read_excel(tool_file, dtype=str).fillna("")
    except Exception as e:
        st.error(f" Failed to read Excel file: {e}")
        st.stop()

    try:
        df_qc = load_qc_log()
    except Exception as e:
        st.error(f" Failed to load QC_Log: {e}")
        st.stop()

    if selected_user == "All":
        df_qc_user = df_qc.copy()
    else:
        df_qc_user = df_qc[df_qc["QC By"] == selected_user]

    if df_qc_user.empty:
        st.info("✅ No keys assigned to you in QC_Log.")
    else:
        issues = []

        for idx, row in df_tool.iterrows():
            key = str(row.get("KEY", "")).strip()
            if key == "":
                continue

            qc_row = df_qc_user[df_qc_user["KEY"] == key]
            if qc_row.empty:
                continue

            status_qc = str(qc_row.iloc[0].get("Status", "")).upper().strip()
            if status_qc != "APPROVED":
                continue

            consent = str(row.get("Consent", "")).strip()
            name = str(row.get("Full_name_of_respondent", "")).strip()
            phone = str(row.get("Respondents_phone_number", "")).strip()
            final_comments = str(row.get("Final_comments", "")).strip()
            final_translation = str(row.get("Final_comments_Translation", "")).strip()
            qa_status = str(row.get("QA_status", "")).strip().upper()
            review_status = str(row.get("review_status", "")).strip().upper()
            qa_by = str(qc_row.iloc[0]["QC By"]).strip()

            criteria = str(row.get("selection_criteria_subject_grade_availability", "")).strip()
            other_specify = str(row.get("selection_other_specify", "")).strip()
            female_accom = str(row.get("female_accommodation_provided", "")).strip()
            female_support = str(row.get("female_support_details", "")).strip()
            challenge_flag = str(row.get("training_attendance_challenges", "")).strip()
            challenge_details = str(row.get("challenge_details", "")).strip()

            if consent == "0":
                issues.append({"KEY": key, "Tool": "Tool 10", "QA_By": qa_by,
                               "Question_Label": "Consent", "Issue": "Form cannot be No Consent.", "Choice": consent})

            if name and not all(ord(c) < 128 for c in name):
                issues.append({"KEY": key, "Tool": "Tool 10", "QA_By": qa_by,
                               "Question_Label": "Full_name_of_respondent", "Issue": "Respondent name must be in English.", "Choice": name})

            if not ((phone.startswith("07") and len(phone) == 10 and phone.isdigit()) or phone == "0000000000"):
                issues.append({"KEY": key, "Tool": "Tool 10", "QA_By": qa_by,
                               "Question_Label": "Respondents_phone_number",
                               "Issue": "Phone number must be 10 digits starting with 07 or exactly 0000000000.",
                               "Choice": phone})

            if final_comments and (final_translation in ["", "-"]):
                issues.append({"KEY": key, "Tool": "Tool 10", "QA_By": qa_by,
                               "Question_Label": "Final_comments_Translation", "Issue": "Final comment must be translated.", "Choice": final_translation})

            if qa_status not in ["", "APP", "REJ"]:
                issues.append({"KEY": key, "Tool": "Tool 10", "QA_By": qa_by,
                               "Question_Label": "QA_status", "Issue": "QA_status must be APP or REJ only.", "Choice": qa_status})

            if qa_status == "APP" and review_status != "APPROVED":
                issues.append({"KEY": key, "Tool": "Tool 10", "QA_By": qa_by,
                               "Question_Label": "review_status", "Issue": "If QA_status is APP, review_status must be APPROVED.", "Choice": review_status})

            if qa_status == "REJ" and review_status != "REJECTED":
                issues.append({"KEY": key, "Tool": "Tool 10", "QA_By": qa_by,
                               "Question_Label": "review_status", "Issue": "If QA_status is REJ, review_status must be REJECTED.", "Choice": review_status})

            if review_status in ["APPROVED", "REJECTED"] and qa_status in ["", "-"]:
                issues.append({"KEY": key, "Tool": "Tool 10", "QA_By": qa_by,
                               "Question_Label": "QA_status", "Issue": "If review_status is APPROVED/REJECTED, QA_status cannot be blank.", "Choice": qa_status})

            if (qa_by == "-" or qa_status == "-") and review_status in ["APPROVED", "REJECTED"]:
                issues.append({"KEY": key, "Tool": "Tool 10", "QA_By": qa_by,
                               "Question_Label": "QA_By/QA_status", "Issue": "QA_By or QA_status cannot be '-' when review_status is APPROVED/REJECTED.", "Choice": f"{qa_by}/{qa_status}"})

            if "8888" in criteria.split(","):
                if other_specify in ["", "-", None]:
                    issues.append({"KEY": key, "Tool": "Tool 10", "QA_By": qa_by,
                                   "Question_Label": "selection_other_specify", "Issue": "Cannot be blank when 8888 is selected. Please provide reason in English.", "Choice": other_specify})
                elif not all(ord(c) < 128 for c in other_specify):
                    issues.append({"KEY": key, "Tool": "Tool 10", "QA_By": qa_by,
                                   "Question_Label": "selection_other_specify", "Issue": "Must be in English. Please translate.", "Choice": other_specify})

            if female_accom == "1":
                if female_support in ["", "-", None]:
                    issues.append({"KEY": key, "Tool": "Tool 10", "QA_By": qa_by,
                                   "Question_Label": "female_support_details", "Issue": "Cannot be blank when female_accommodation_provided is 1.", "Choice": female_support})
                elif not all(ord(c) < 128 for c in female_support):
                    issues.append({"KEY": key, "Tool": "Tool 10", "QA_By": qa_by,
                                   "Question_Label": "female_support_details", "Issue": "Must be in English. Please translate.", "Choice": female_support})

            if challenge_flag == "1":
                if challenge_details in ["", "-", None]:
                    issues.append({"KEY": key, "Tool": "Tool 10", "QA_By": qa_by,
                                   "Question_Label": "challenge_details", "Issue": "Cannot be blank when training_attendance_challenges is 1.", "Choice": challenge_details})
                elif not all(ord(c) < 128 for c in challenge_details):
                    issues.append({"KEY": key, "Tool": "Tool 10", "QA_By": qa_by,
                                   "Question_Label": "challenge_details", "Issue": "Must be in English. Please translate.", "Choice": challenge_details})

        if issues:
            df_issues = pd.DataFrame(issues, columns=["KEY", "Tool", "QA_By", "Question_Label", "Issue", "Choice"])
            st.error(f"⚠ {len(df_issues)} issues detected.")
            st.dataframe(df_issues)

            buffer = BytesIO()
            df_issues.to_excel(buffer, index=False)
            buffer.seek(0)
            st.download_button(
                label="⬇ Download Issues Report",
                data=buffer,
                file_name=f"Tool10_Issues_{selected_user}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        else:
            st.success("✅ No issues found for your assigned keys.")
