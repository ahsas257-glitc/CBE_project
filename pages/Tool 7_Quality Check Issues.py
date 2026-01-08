import pandas as pd
import streamlit as st
from io import BytesIO
import gspread
from google.oauth2.service_account import Credentials

st.set_page_config(page_title="Tool 7 QC Issues", layout="wide")
st.title("🛠 Tool 7 QC Issues")

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

tool_file = st.file_uploader("Upload Tool 7 Excel File", type=["xlsx"])

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

            qa_by = str(qc_row.iloc[0]["QC By"]).strip()
            consent_informed = str(row.get("Consent_Informed", "")).strip()

            # ==========================
            # CASE: Consent_Informed = 0
            # ==========================
            if consent_informed == "0":
                # Check Remark in Google Sheet
                remark = str(qc_row.iloc[0].get("Remark", "")).strip()
                if not remark or not all(ord(c) < 128 for c in remark):
                    issues.append({
                        "KEY": key, "Tool": "Tool 7", "QA_By": qa_by,
                        "Question_Label": "Remark",
                        "Issue": "Consent_Informed is 'No'. Remark must clearly explain in English why consent was not taken.",
                        "Choice": remark
                    })

                # Check Final_comments + Translation
                final_comments = str(row.get("Final_comments", "")).strip()
                final_translation = str(row.get("Final_comments_Translation", "")).strip()
                if final_comments and (final_translation in ["", "-"]):
                    issues.append({
                        "KEY": key, "Tool": "Tool 7", "QA_By": qa_by,
                        "Question_Label": "Final_comments_Translation",
                        "Issue": "Final comment must be translated when consent is not given.",
                        "Choice": final_translation
                    })
                # Skip all other checks
                continue

            # ==========================
            # CASE: Consent_Informed = 1 → Normal checks
            # ==========================
            resp_name = str(row.get("Resp_name", "")).strip()
            if not resp_name or not all(ord(c) < 128 for c in resp_name):
                issues.append({
                    "KEY": key, "Tool": "Tool 7", "QA_By": qa_by,
                    "Question_Label": "Resp_name",
                    "Issue": "Name cannot be blank or non-English. Translate to English or fill correctly.",
                    "Choice": resp_name
                })

            resp_desig = str(row.get("Resp_designation", "")).strip()
            resp_desig_other = str(row.get("Resp_designation_other", "")).strip()
            if "8888" in resp_desig.split(","):
                if not resp_desig_other or not all(ord(c) < 128 for c in resp_desig_other):
                    issues.append({
                        "KEY": key, "Tool": "Tool 7", "QA_By": qa_by,
                        "Question_Label": "Resp_designation_other",
                        "Issue": "Cannot be blank or non-English when 8888 selected. Translate and correct.",
                        "Choice": resp_desig_other
                    })

            resp_phone = str(row.get("Resp_phone", "")).strip()
            if not ((resp_phone.startswith("07") and len(resp_phone) == 10 and resp_phone.isdigit()) or resp_phone == "0000000000"):
                issues.append({
                    "KEY": key, "Tool": "Tool 7", "QA_By": qa_by,
                    "Question_Label": "Resp_phone",
                    "Issue": "Phone must start with 07 or be 0000000000. Correct number.",
                    "Choice": resp_phone
                })

            sms_date = str(row.get("sms_established_date", "")).strip()
            if sms_date.startswith("2025"):
                issues.append({
                    "KEY": key, "Tool": "Tool 7", "QA_By": qa_by,
                    "Question_Label": "sms_established_date",
                    "Issue": "Date cannot be in 2025. Verify correct date.",
                    "Choice": sms_date
                })

            qa_status = str(row.get("QA_status", "")).strip().upper()
            review_status = str(row.get("review_status", "")).strip().upper()

            if qa_status not in ["", "APP", "REJ"]:
                issues.append({"KEY": key, "Tool": "Tool 7", "QA_By": qa_by,
                               "Question_Label": "QA_status", "Issue": "QA_status must be APP or REJ only.",
                               "Choice": qa_status})

            if qa_status == "APP" and review_status != "APPROVED":
                issues.append({"KEY": key, "Tool": "Tool 7", "QA_By": qa_by,
                               "Question_Label": "review_status", "Issue": "If QA_status is APP, review_status must be APPROVED.",
                               "Choice": review_status})

            if qa_status == "REJ" and review_status != "REJECTED":
                issues.append({"KEY": key, "Tool": "Tool 7", "QA_By": qa_by,
                               "Question_Label": "review_status", "Issue": "If QA_status is REJ, review_status must be REJECTED.",
                               "Choice": review_status})

            if review_status in ["APPROVED", "REJECTED"] and qa_status in ["", "-"]:
                issues.append({"KEY": key, "Tool": "Tool 7", "QA_By": qa_by,
                               "Question_Label": "QA_status", "Issue": "If review_status is APPROVED/REJECTED, QA_status cannot be blank.",
                               "Choice": qa_status})

            if (qa_by == "-" or qa_status == "-") and review_status in ["APPROVED", "REJECTED"]:
                issues.append({"KEY": key, "Tool": "Tool 7", "QA_By": qa_by,
                               "Question_Label": "QA_By/QA_status", "Issue": "QA_By or QA_status cannot be '-' when review_status is APPROVED/REJECTED.",
                               "Choice": f"{qa_by}/{qa_status}"})

            final_comments = str(row.get("Final_comments", "")).strip()
            final_translation = str(row.get("Final_comments_Translation", "")).strip()
            if final_comments and (final_translation in ["", "-"]):
                issues.append({"KEY": key, "Tool": "Tool 7", "QA_By": qa_by,
                               "Question_Label": "Final_comments_Translation", "Issue": "Final comment must be translated.",
                               "Choice": final_translation})
            if not final_comments and final_translation not in ["-", ""]:
                issues.append({"KEY": key, "Tool": "Tool 7", "QA_By": qa_by,
                               "Question_Label": "Final_comments_Translation", "Issue": "No comment exists, translation must be '-'.",
                               "Choice": final_translation})

        # ==========================
        # Export issues
        # ==========================
        if issues:
            df_issues = pd.DataFrame(issues, columns=["KEY", "Tool", "QA_By", "Question_Label", "Issue", "Choice"])
            df_issues = df_issues.astype(str)
            st.error(f"⚠ {len(df_issues)} issues detected.")
            st.dataframe(df_issues)

            buffer = BytesIO()
            df_issues.to_excel(buffer, index=False)
            buffer.seek(0)
            st.download_button(
                label="⬇ Download Issues Report",
                data=buffer,
                file_name=f"Tool7_Issues_{selected_user}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        else:
            st.success("✅ No issues found for your assigned keys.")
