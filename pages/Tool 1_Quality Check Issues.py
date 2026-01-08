import pandas as pd
import streamlit as st
from io import BytesIO
import gspread
from google.oauth2.service_account import Credentials
import re

st.set_page_config(page_title="Tool 1 QC Issues", layout="wide")
st.title("🛠 Tool 1 QC Issues")

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

_PERSO_ARABIC_RE = re.compile(r'[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF]')

def is_english_text_strict(text):
    if text is None:
        return False
    s = str(text).strip()
    if s == "":
        return False
    return _PERSO_ARABIC_RE.search(s) is None

is_english_text = is_english_text_strict
is_english = is_english_text_strict

def parse_choices(val):
    if val is None:
        return []
    return [c.strip() for c in re.split(r'[,\s]+', str(val)) if c.strip() != ""]

users = ["All",
         "Waris Amini", "Shabeer Ahmad Ahsas", "Romal wali",
         "Abrahim Ahrahimi", "Abdullah Deldar", "Hedayatullah Setanikzai",
         "A.Azim Hashimi", "Abed Ahmadzai", "Ahmad Akbari",
         "Inamullah Salamzai", "Hashmatullah Amarkhil", "Jalil Ahmad Jamal",
         "Khalid Ammar", "M.Samim Kohistani", "Meena Yawari",
         "Noryalai Hotak", "Sejadullah Safi", "Shahedullah Noorzad"]
selected_user = st.selectbox("Select your name", users)

tool_file = st.file_uploader("Upload Tool 1 Excel File", type=["xlsx"])

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

            review_status = str(row.get("review_status", "")).upper().strip()
            qa_status = str(row.get("QA_status", "")).strip().upper()
            qa_by = str(qc_row.iloc[0].get("QC By", "")).strip()
            consent_informed = str(row.get("Consent_Informed", "")).strip()

            if review_status != "APPROVED":
                continue

            if consent_informed == "0":
                final_comments = str(row.get("Final_comments", "")).strip()
                final_translation = str(row.get("Final_comments_Translation", "")).strip()
                remark = str(qc_row.iloc[0].get("Remark", "")).strip()

                if final_comments and (final_translation in ["", "-"]):
                    issues.append({
                        "KEY": key, "Tool": "Tool 1", "QA_By": qa_by,
                        "Question_Label": "Final_comments_Translation",
                        "Issue": "When Consent=0 and Final_comments is filled, Final_comments_Translation must not be blank or '-'. Translate the final comment to English.",
                        "Choice": final_translation
                    })

                if not remark or not is_english_text(remark):
                    issues.append({
                        "KEY": key, "Tool": "Tool 1", "QA_By": qa_by,
                        "Question_Label": "Remark",
                        "Issue": "When Consent=0, QC_Log Remark must be present and in English explaining why consent was not taken.",
                        "Choice": remark
                    })
                continue

            final_comments = str(row.get("Final_comments", "")).strip()
            final_translation = str(row.get("Final_comments_Translation", "")).strip()
            if final_comments and (final_translation in ["", "-"]):
                issues.append({"KEY": key, "Tool": "Tool 1", "QA_By": qa_by,
                               "Question_Label": "Final_comments_Translation",
                               "Issue": "Final comment must be translated when form is approved.",
                               "Choice": final_translation})

            if qa_status != "APP":
                issues.append({"KEY": key, "Tool": "Tool 1", "QA_By": qa_by,
                               "Question_Label": "QA_status",
                               "Issue": "If review_status=APPROVED, QA_status must be APP.",
                               "Choice": qa_status})

            resp_name = str(row.get("Resp_name", "")).strip()
            if not resp_name or not is_english_text_strict(resp_name):
                issues.append({
                    "KEY": key,
                    "Tool": "Tool 1",
                    "QA_By": qa_by,
                    "Question_Label": "Resp_name",
                    "Issue": "Resp_name must not be blank and must not contain Persian/Dari or Pashto letters.",
                    "Choice": resp_name
                })

            resp_title = str(row.get("Resp_title", "")).strip()
            remark = str(qc_row.iloc[0].get("Remark", "")).strip()
            if resp_title == "2" and (not remark or not is_english_text(remark)):
                issues.append({"KEY": key, "Tool": "Tool 1", "QA_By": qa_by,
                               "Question_Label": "Resp_title/Remark",
                               "Issue": "When Resp_title=2, QC_Log Remark must not be blank or non-English.",
                               "Choice": remark})

            resp_phone = str(row.get("Resp_phone", "")).strip()
            if not ((resp_phone.startswith("07") and len(resp_phone) == 10 and resp_phone.isdigit()) or resp_phone == "0000000000"):
                issues.append({"KEY": key, "Tool": "Tool 1", "QA_By": qa_by,
                               "Question_Label": "Resp_phone",
                               "Issue": "Phone must start with 07 and be 10 digits, or be 0000000000.",
                               "Choice": resp_phone})

            resp_comm = str(row.get("Resp_communities", "")).strip()
            resp_comm_other = str(row.get("Resp_communities_IP_other", "")).strip()
            if "8888" in [c.strip() for c in resp_comm.split(",") if c.strip()]:
                if not resp_comm_other or not is_english_text(resp_comm_other):
                    issues.append({"KEY": key, "Tool": "Tool 1", "QA_By": qa_by,
                                   "Question_Label": "Resp_communities_IP_other",
                                   "Issue": "When Resp_communities includes '8888', Resp_communities_IP_other must not be blank and must be in English.",
                                   "Choice": resp_comm_other})

            cbe_date = str(row.get("CBE_date_establishment", "")).strip()
            if cbe_date.startswith("2025") or cbe_date.startswith("2024"):
                issues.append({"KEY": key, "Tool": "Tool 1", "QA_By": qa_by,
                               "Question_Label": "CBE_date_establishment",
                               "Issue": "CBE establishment date must not be in 2024 or 2025.",
                               "Choice": cbe_date})

            closure_reason = str(row.get("cbe_closure_reason", "")).strip()
            closure_reason_other = str(row.get("cbe_closure_reason_other", "")).strip()
            if closure_reason == "8888" and (not closure_reason_other or not is_english_text_strict(closure_reason_other)):
                issues.append({
                    "KEY": key, "Tool": "Tool 1", "QA_By": qa_by,
                    "Question_Label": "cbe_closure_reason_other",
                    "Issue": "When cbe_closure_reason=8888, cbe_closure_reason_other must not be blank and must not contain Persian or Pashto letters.",
                    "Choice": closure_reason_other
                })

            closure_boys = str(row.get("cbe_closure_boys_schooling", "")).strip()
            closure_boys_other = str(row.get("cbe_closure_boys_schooling_other", "")).strip()
            if closure_boys == "8888" and (not closure_boys_other or not is_english_text(closure_boys_other)):
                issues.append({"KEY": key, "Tool": "Tool 1", "QA_By": qa_by,
                               "Question_Label": "cbe_closure_boys_schooling_other",
                               "Issue": "When cbe_closure_boys_schooling=8888, cbe_closure_boys_schooling_other must not be blank and must be in English.",
                               "Choice": closure_boys_other})

            cbe_closure_girls = str(row.get("cbe_closure_girls_schooling", "")).strip()
            cbe_closure_girls_other = str(row.get("cbe_closure_girls_schooling_other", "")).strip()
            if cbe_closure_girls == "8888":
                if not cbe_closure_girls_other or not is_english_text(cbe_closure_girls_other):
                    issues.append({"KEY": key, "Tool": "Tool 1", "QA_By": qa_by,
                                   "Question_Label": "cbe_closure_girls_schooling_other",
                                   "Issue": "When cbe_closure_girls_schooling=8888, cbe_closure_girls_schooling_other must not be blank and must be in English.",
                                   "Choice": cbe_closure_girls_other})

            closure_fields = [
                "cbe_open_this_year", "cbe_last_operational_time", "cbe_closure_reason",
                "cbe_closure_reason_other", "cbe_closure_type", "cbe_closure_date_range",
                "cbe_closure_boys_schooling", "cbe_closure_boys_schooling_other",
                "cbe_closure_girls_schooling", "cbe_closure_girls_schooling_other",
                "cbe_reopening_plans"
            ]

            cbe_location_type = str(row.get("cbe_location_type", "")).strip()
            if cbe_location_type == "8888":
                issues.append({"KEY": key, "Tool": "Tool 1", "QA_By": qa_by,
                               "Question_Label": "cbe_location_type",
                               "Issue": "cbe_location_type=8888. Please review the form and select the correct choice from the codebook.",
                               "Choice": cbe_location_type})

            cbe_location_type_other = str(row.get("cbe_location_type_other", "")).strip()
            if "8888" not in [c.strip() for c in cbe_location_type.split(",") if c.strip()]:
                if cbe_location_type_other:
                    issues.append({"KEY": key, "Tool": "Tool 1", "QA_By": qa_by,
                                   "Question_Label": "cbe_location_type_other",
                                   "Issue": "cbe_location_type_other must be blank unless cbe_location_type includes '8888'.",
                                   "Choice": cbe_location_type_other})

            instr_lang = str(row.get("Instruction_Language", "")).strip()
            if "8888" in [c.strip() for c in instr_lang.split(",") if c.strip()]:
                issues.append({"KEY": key, "Tool": "Tool 1", "QA_By": qa_by,
                               "Question_Label": "Instruction_Language",
                               "Issue": "Instruction_Language must not contain '8888'. Choose the correct language code (Pashto or Dari).",
                               "Choice": instr_lang})

            instr_lang_other = str(row.get("Instruction_Language_Other", "")).strip()
            if "8888" not in [c.strip() for c in instr_lang.split(",") if c.strip()]:
                if instr_lang_other:
                    issues.append({"KEY": key, "Tool": "Tool 1", "QA_By": qa_by,
                                   "Question_Label": "Instruction_Language_Other",
                                   "Issue": "Instruction_Language_Other must be blank when Instruction_Language does not include '8888'.",
                                   "Choice": instr_lang_other})

            cbe_type = str(row.get("cbe_type", "")).strip()
            alc_level = str(row.get("alc_level", "")).strip()
            if cbe_type in ["2", "3"]:
                if not alc_level:
                    issues.append({"KEY": key, "Tool": "Tool 1", "QA_By": qa_by,
                                   "Question_Label": "alc_level",
                                   "Issue": "When cbe_type is 2 or 3, alc_level must not be blank and must be a single digit.",
                                   "Choice": alc_level})
                else:
                    if not (alc_level.isdigit() and len(alc_level) == 1):
                        issues.append({"KEY": key, "Tool": "Tool 1", "QA_By": qa_by,
                                       "Question_Label": "alc_level",
                                       "Issue": "alc_level must be a single digit number when required.",
                                       "Choice": alc_level})

            is_islamic_center = str(row.get("is_islamic_center", "")).strip()
            if "1" in [c.strip() for c in is_islamic_center.split(",") if c.strip()]:
                issues.append({"KEY": key, "Tool": "Tool 1", "QA_By": qa_by,
                               "Question_Label": "is_islamic_center",
                               "Issue": "is_islamic_center includes '1'. This is a sensitive question — review carefully and follow up with respondent.",
                               "Choice": is_islamic_center})

            if is_islamic_center == "0":
                for f in ["islamic_center_type", "islamic_center_type_other"]:
                    if str(row.get(f, "")).strip():
                        issues.append({"KEY": key, "Tool": "Tool 1", "QA_By": qa_by,
                                       "Question_Label": f,
                                       "Issue": f"When is_islamic_center=0, '{f}' must be blank.",
                                       "Choice": row.get(f, "")})

            linked_to_hub = str(row.get("linked_to_hub_school", "")).strip()
            linked_name = str(row.get("linked_hub_school_name", "")).strip()
            if "1" in [c.strip() for c in linked_to_hub.split(",") if c.strip()]:
                if not linked_name or not is_english_text_strict(linked_name):
                    issues.append({
                        "KEY": key,
                        "Tool": "Tool 1",
                        "QA_By": qa_by,
                        "Question_Label": "linked_hub_school_name",
                        "Issue": "If linked_to_hub_school=1, linked_hub_school_name must not be blank and must not contain Persian/Dari or Pashto letters.",
                        "Choice": linked_name
                    })

            linked_tpm = str(row.get("linked_hub_school_TPM_ID", "")).strip()
            if linked_tpm and linked_tpm != "-":
                issues.append({"KEY": key, "Tool": "Tool 1", "QA_By": qa_by,
                               "Question_Label": "linked_hub_school_TPM_ID",
                               "Issue": "linked_hub_school_TPM_ID must contain only '-' when applicable.",
                               "Choice": linked_tpm})

            linked_emis = str(row.get("linked_hub_school_EMIS_ID", "")).strip()
            if "1" in [c.strip() for c in linked_to_hub.split(",") if c.strip()]:
                if linked_emis == "-" or linked_emis == "":
                    issues.append({"KEY": key, "Tool": "Tool 1", "QA_By": qa_by,
                                   "Question_Label": "linked_hub_school_EMIS_ID",
                                   "Issue": "When linked_to_hub_school=1, linked_hub_school_EMIS_ID must not be '-' or blank. It should be numeric, 'Not found', or two values separated by '|'.",
                                   "Choice": linked_emis})
                else:
                    em = linked_emis.strip()
                    if "|" in em:
                        parts = [p.strip() for p in em.split("|") if p.strip()]
                        if not parts:
                            issues.append({"KEY": key, "Tool": "Tool 1", "QA_By": qa_by,
                                           "Question_Label": "linked_hub_school_EMIS_ID",
                                           "Issue": "linked_hub_school_EMIS_ID has '|' but no valid parts.",
                                           "Choice": linked_emis})
                    elif em.lower() == "not found":
                        pass
                    elif em.isdigit():
                        pass
                    else:
                        issues.append({"KEY": key, "Tool": "Tool 1", "QA_By": qa_by,
                                       "Question_Label": "linked_hub_school_EMIS_ID",
                                       "Issue": "linked_hub_school_EMIS_ID must be numeric, 'Not found', or values separated by '|'. Please correct EMIS ID.",
                                       "Choice": linked_emis})
            # ✅ Rule: If linked_to_hub_school = 1, then distance_to_hub_school_km must be between 1 and 20 (and not blank)
            linked_to_hub = str(row.get("linked_to_hub_school", "")).strip()
            distance_val = str(row.get("distance_to_hub_school_km", "")).strip()

            if linked_to_hub == "1":
                if not distance_val:
                    issues.append({
                        "KEY": key,
                        "Tool": "Tool 1",
                        "QA_By": qa_by,
                        "Question_Label": "distance_to_hub_school_km",
                        "Issue": "When linked_to_hub_school = 1, distance_to_hub_school_km must not be blank.",
                        "Choice": distance_val
                    })
                else:
                    try:
                        distance_num = float(distance_val)
                        if distance_num < 1 or distance_num > 20:
                            issues.append({
                                "KEY": key,
                                "Tool": "Tool 1",
                                "QA_By": qa_by,
                                "Question_Label": "distance_to_hub_school_km",
                                "Issue": f"When linked_to_hub_school = 1, distance_to_hub_school_km must be between 1 and 20 (found {distance_num}).",
                                "Choice": distance_num
                            })
                    except ValueError:
                        issues.append({
                            "KEY": key,
                            "Tool": "Tool 1",
                            "QA_By": qa_by,
                            "Question_Label": "distance_to_hub_school_km",
                            "Issue": "distance_to_hub_school_km must be numeric when linked_to_hub_school = 1.",
                            "Choice": distance_val
                        })

            num_male = str(row.get("num_male_teachers_teaching", "")).strip()
            num_female = str(row.get("num_female_teachers_teaching", "")).strip()
            if num_male == "0" and num_female == "0":
                issues.append({
                    "KEY": key, "Tool": "Tool 1", "QA_By": qa_by,
                    "Question_Label": "num_male_teachers_teaching/num_female_teachers_teaching",
                    "Issue": "Review form again: It is impossible for class to have neither male nor female teachers.",
                    "Choice": f"{num_male}/{num_female}"
                })

            total_teaching = str(row.get("num_total_teachers_teaching", "")).strip()
            if total_teaching.isdigit() and int(total_teaching) > 3:
                issues.append({
                    "KEY": key, "Tool": "Tool 1", "QA_By": qa_by,
                    "Question_Label": "num_total_teachers_teaching",
                    "Issue": "Review form again: Number of teachers exceeds the allowed limit.",
                    "Choice": total_teaching
                })

            total_present = str(row.get("num_total_teachers_present", "")).strip()
            if total_present.isdigit() and int(total_present) > 3:
                issues.append({
                    "KEY": key, "Tool": "Tool 1", "QA_By": qa_by,
                    "Question_Label": "num_total_teachers_present",
                    "Issue": "Review form again: Number of teachers exceeds the allowed limit.",
                    "Choice": total_present
                })

            dis_reg = str(row.get("registered_students_with_disability", "")).strip()
            boys_dis = str(row.get("registered_boys_with_disability", "")).strip()
            girls_dis = str(row.get("registered_girls_with_disability", "")).strip()
            dis_type = str(row.get("disability_type", "")).strip()
            if dis_reg == "0":
                if boys_dis != "0" or girls_dis != "0" or dis_type:
                    issues.append({
                        "KEY": key, "Tool": "Tool 1", "QA_By": qa_by,
                        "Question_Label": "registered_students_with_disability",
                        "Issue": "Review form again: If no disabled students, counts must be 0 and disability_type must be blank.",
                        "Choice": f"{boys_dis}/{girls_dis}/{dis_type}"
                    })

            if dis_reg == "1":
                if (not boys_dis.isdigit() or int(boys_dis) == 0) and (not girls_dis.isdigit() or int(girls_dis) == 0):
                    issues.append({
                        "KEY": key, "Tool": "Tool 1", "QA_By": qa_by,
                        "Question_Label": "registered_students_with_disability",
                        "Issue": "If disabled students registered, at least one of boys/girls must be > 0.",
                        "Choice": f"{boys_dis}/{girls_dis}"
                    })

            dis_reg = str(row.get("disability_registered", "")).strip()
            dis_type = str(row.get("disability_type", "")).strip()
            if dis_reg == "1":
                if not dis_type or not is_english_text_strict(dis_type):
                    issues.append({
                        "KEY": key,
                        "Tool": "Tool 1",
                        "QA_By": qa_by,
                        "Question_Label": "disability_type",
                        "Issue": "If disability_registered=1, disability_type must not be blank and must not contain Persian/Dari or Pashto letters.",
                        "Choice": dis_type
                    })

            dropout_count = str(row.get("registered_students_dropped_out", "")).strip()
            dropout_reason = str(row.get("dropout_reasons", "")).strip()
            dropout_reason_other = str(row.get("dropout_reasons_other", "")).strip()
            if dropout_count.isdigit() and int(dropout_count) > 0:
                if not dropout_reason:
                    issues.append({
                        "KEY": key, "Tool": "Tool 1", "QA_By": qa_by,
                        "Question_Label": "dropout_reasons",
                        "Issue": "Review form: dropout_reasons must not be blank when students dropped out > 0.",
                        "Choice": dropout_reason
                    })
            if "8888" in dropout_reason.split(","):
                if not dropout_reason_other or not is_english_text_strict(dropout_reason_other):
                    issues.append({
                        "KEY": key,
                        "Tool": "Tool 1",
                        "QA_By": qa_by,
                        "Question_Label": "dropout_reasons_other",
                        "Issue": "If 8888 is selected in dropout_reasons, dropout_reasons_other must not be blank and must not contain Persian/Dari or Pashto letters.",
                        "Choice": dropout_reason_other
                    })

            allowed_photos = ["Relevant Photo", "Irrelevant Photo", "Blur/Not Visible Photo"]
            students_picture = str(row.get("students_picture_QA", "")).strip()
            if students_picture and students_picture not in allowed_photos:
                issues.append({
                    "KEY": key, "Tool": "Tool 1", "QA_By": qa_by,
                    "Question_Label": "students_picture_QA",
                    "Issue": "Value must only be one of: Relevant Photo / Irrelevant Photo / Blur/Not Visible Photo.",
                    "Choice": students_picture
                })

            absent_10 = str(row.get("students_absent_10_days", "")).strip()
            reason_audio = str(row.get("reason_absenteeism_audio", "")).strip()
            if absent_10 == "1" and not reason_audio:
                issues.append({
                    "KEY": key, "Tool": "Tool 1", "QA_By": qa_by,
                    "Question_Label": "reason_absenteeism_audio",
                    "Issue": "If student absent 10 days=Yes, audio file must be provided.",
                    "Choice": reason_audio
                })

            reason_translation = str(row.get("reason_absenteeism_translation_QA", "")).strip()
            if reason_audio:
                if not reason_translation or reason_translation == "-":
                    issues.append({
                        "KEY": key, "Tool": "Tool 1", "QA_By": qa_by,
                        "Question_Label": "reason_absenteeism_translation_QA",
                        "Issue": "Reason for absenteeism must be translated; cannot be blank or '-'.",
                        "Choice": reason_translation
                    })

            if "no comment" in reason_translation.lower():
                issues.append({
                    "KEY": key, "Tool": "Tool 1", "QA_By": qa_by,
                    "Question_Label": "reason_absenteeism_translation_QA",
                    "Issue": "Writing 'No comment' is not allowed in absenteeism translation.",
                    "Choice": reason_translation
                })

            classroom_kit_received = str(row.get("classroom_kit_received", "")).strip()
            classroom_kit_received_count = str(row.get("classroom_kit_received_count", "")).strip()
            if classroom_kit_received == "1" and not classroom_kit_received_count:
                issues.append({
                    "KEY": key, "Tool": "Tool 1", "QA_By": qa_by,
                    "Question_Label": "classroom_kit_received_count",
                    "Issue": "When classroom_kit_received=1, classroom_kit_received_count must not be blank.",
                    "Choice": classroom_kit_received_count
                })

            if classroom_kit_received_count and (classroom_kit_received_count == "0" or int(classroom_kit_received_count) > 3):
                issues.append({
                    "KEY": key, "Tool": "Tool 1", "QA_By": qa_by,
                    "Question_Label": "classroom_kit_received_count",
                    "Issue": "Each class can only receive a kit once per year. Count cannot be 0 or greater than 3.",
                    "Choice": classroom_kit_received_count
                })

            classroom_kit_received_frequency_in_alc = str(row.get("classroom_kit_received_frequency_in_alc", "")).strip()
            classroom_kit_received = str(row.get("classroom_kit_received", "")).strip()

            if cbe_type == "1" and classroom_kit_received == "1":
                if classroom_kit_received_frequency_in_alc:
                    issues.append({
                        "KEY": key,
                        "Tool": "Tool 1",
                        "QA_By": qa_by,
                        "Question_Label": "classroom_kit_received_frequency_in_alc",
                        "Issue": "When cbe_type=1 and classroom_kit_received=1, classroom_kit_received_frequency_in_alc must be blank.",
                        "Choice": classroom_kit_received_frequency_in_alc
                    })

            if cbe_type == "2" and classroom_kit_received == "1":
                if not classroom_kit_received_frequency_in_alc:
                    issues.append({
                        "KEY": key,
                        "Tool": "Tool 1",
                        "QA_By": qa_by,
                        "Question_Label": "classroom_kit_received_frequency_in_alc",
                        "Issue": "When cbe_type=2 and classroom_kit_received=1, classroom_kit_received_frequency_in_alc must not be blank.",
                        "Choice": classroom_kit_received_frequency_in_alc
                    })

            classroom_material_included = str(row.get("classroom_material_included", "")).strip()
            classroom_material_included_other = str(row.get("classroom_material_included_other", "")).strip()
            if "8888" in str(classroom_material_included).split():
                if not classroom_material_included_other or not is_english_text_strict(classroom_material_included_other):
                    issues.append({
                        "KEY": key,
                        "Tool": "Tool 1",
                        "QA_By": qa_by,
                        "Question_Label": "classroom_material_included_other",
                        "Issue": "If 'Other (8888)' is selected, classroom_material_included_other must not be blank and must not contain Persian/Dari or Pashto letters.",
                        "Choice": classroom_material_included_other
                    })

            classroom_materials_count = str(row.get("classroom_materials_count", "")).strip()
            if classroom_material_included and classroom_materials_count:
                included_choices = [c.strip() for c in classroom_material_included.split() if c.strip()]
                try:
                    if len(included_choices) != int(classroom_materials_count):
                        issues.append({
                            "KEY": key, "Tool": "Tool 1", "QA_By": qa_by,
                            "Question_Label": "classroom_materials_count",
                            "Issue": "The number of selected materials must equal classroom_materials_count.",
                            "Choice": classroom_materials_count
                        })
                except ValueError:
                    pass

            classroom_kit_not_received_reason = str(row.get("classroom_kit_not_received_reason", "")).strip()
            learning_disruption_tlm_lack = str(row.get("learning_disruption_tlm_lack", "")).strip()
            classroom_kit_expected = str(row.get("classroom_kit_expected", "")).strip()
            if classroom_kit_received == "0" and (not classroom_kit_not_received_reason or not learning_disruption_tlm_lack or not classroom_kit_expected):
                issues.append({
                    "KEY": key, "Tool": "Tool 1", "QA_By": qa_by,
                    "Question_Label": "classroom_kit_received",
                    "Issue": "When classroom_kit_received=0, the reasons and expected kit info must not be blank.",
                    "Choice": classroom_kit_received
                })

            classroom_kit_not_received_reason_other = str(row.get("classroom_kit_not_received_reason_other", "")).strip()
            if "8888" in str(classroom_kit_not_received_reason).split():
                if not classroom_kit_not_received_reason_other or not is_english_text_strict(classroom_kit_not_received_reason_other):
                    issues.append({
                        "KEY": key,
                        "Tool": "Tool 1",
                        "QA_By": qa_by,
                        "Question_Label": "classroom_kit_not_received_reason_other",
                        "Issue": "If 'Other (8888)' is selected, classroom_kit_not_received_reason_other must not be blank and must not contain Persian/Dari or Pashto letters.",
                        "Choice": classroom_kit_not_received_reason_other
                    })

            classroom_kit_grouped_photo = str(row.get("classroom_kit_grouped_photo", "")).strip()
            classroom_kit_in_use_1 = str(row.get("classroom_kit_in_use_1", "")).strip()
            if "1" in classroom_kit_grouped_photo and not classroom_kit_in_use_1:
                issues.append({
                    "KEY": key, "Tool": "Tool 1", "QA_By": qa_by,
                    "Question_Label": "classroom_kit_in_use_1",
                    "Issue": "If option 1 is selected in classroom_kit_grouped_photo, classroom_kit_in_use_1 must not be blank.",
                    "Choice": classroom_kit_in_use_1
                })

            classroom_kit_in_use_1_QA = str(row.get("classroom_kit_in_use_1_QA", "")).strip()
            allowed_photos = ["Blur/Not Visible Photo", "Relevant Photo", "Irrelevant Photo"]
            if classroom_kit_in_use_1 and (not classroom_kit_in_use_1_QA or classroom_kit_in_use_1_QA not in allowed_photos):
                issues.append({
                    "KEY": key, "Tool": "Tool 1", "QA_By": qa_by,
                    "Question_Label": "classroom_kit_in_use_1_QA",
                    "Issue": "If classroom_kit_in_use_1 has value, QA must be one of: Blur/Not Visible Photo, Relevant Photo, Irrelevant Photo.",
                    "Choice": classroom_kit_in_use_1_QA
                })

            classroom_kit_in_use_2 = str(row.get("classroom_kit_in_use_2", "")).strip()
            classroom_kit_in_use_2_QA = str(row.get("classroom_kit_in_use_2_QA", "")).strip()
            if classroom_kit_in_use_2 and (not classroom_kit_in_use_2_QA or classroom_kit_in_use_2_QA not in allowed_photos):
                issues.append({
                    "KEY": key, "Tool": "Tool 1", "QA_By": qa_by,
                    "Question_Label": "classroom_kit_in_use_2_QA",
                    "Issue": "If classroom_kit_in_use_2 has value, QA must be one of: Blur/Not Visible Photo, Relevant Photo, Irrelevant Photo.",
                    "Choice": classroom_kit_in_use_2_QA
                })

            classroom_kit_not_in_use_1 = str(row.get("classroom_kit_not_in_use_1", "")).strip()
            if "2" in classroom_kit_grouped_photo and not classroom_kit_not_in_use_1:
                issues.append({
                    "KEY": key, "Tool": "Tool 1", "QA_By": qa_by,
                    "Question_Label": "classroom_kit_not_in_use_1",
                    "Issue": "If option 2 is selected in classroom_kit_grouped_photo, classroom_kit_not_in_use_1 must not be blank.",
                    "Choice": classroom_kit_not_in_use_1
                })

            classroom_kit_not_in_use_1_QA = str(row.get("classroom_kit_not_in_use_1_QA", "")).strip()
            if classroom_kit_not_in_use_1 and (not classroom_kit_not_in_use_1_QA or classroom_kit_not_in_use_1_QA not in allowed_photos):
                issues.append({
                    "KEY": key, "Tool": "Tool 1", "QA_By": qa_by,
                    "Question_Label": "classroom_kit_not_in_use_1_QA",
                    "Issue": "If classroom_kit_not_in_use_1 has value, QA must be one of: Blur/Not Visible Photo, Relevant Photo, Irrelevant Photo.",
                    "Choice": classroom_kit_not_in_use_1_QA
                })

            classroom_kit_not_in_use_2 = str(row.get("classroom_kit_not_in_use_2", "")).strip()
            classroom_kit_not_in_use_2_QA = str(row.get("classroom_kit_not_in_use_2_QA", "")).strip()
            if classroom_kit_not_in_use_2 and (not classroom_kit_not_in_use_2_QA or classroom_kit_not_in_use_2_QA not in allowed_photos):
                issues.append({
                    "KEY": key, "Tool": "Tool 1", "QA_By": qa_by,
                    "Question_Label": "classroom_kit_not_in_use_2_QA",
                    "Issue": "If classroom_kit_not_in_use_2 has value, QA must be one of: Blur/Not Visible Photo, Relevant Photo, Irrelevant Photo.",
                    "Choice": classroom_kit_not_in_use_2_QA
                })

            if "3" in classroom_kit_grouped_photo:
                if classroom_kit_in_use_1 or classroom_kit_in_use_2 or classroom_kit_not_in_use_1 or classroom_kit_not_in_use_2:
                    issues.append({
                        "KEY": key, "Tool": "Tool 1", "QA_By": qa_by,
                        "Question_Label": "classroom_kit_grouped_photo",
                        "Issue": "If option 3 is selected, all in_use/not_in_use fields must be blank.",
                        "Choice": classroom_kit_grouped_photo
                    })
                for qa_field, qa_value in [
                    ("classroom_kit_in_use_1_QA", classroom_kit_in_use_1_QA),
                    ("classroom_kit_in_use_2_QA", classroom_kit_in_use_2_QA),
                    ("classroom_kit_not_in_use_1_QA", classroom_kit_not_in_use_1_QA),
                    ("classroom_kit_not_in_use_2_QA", classroom_kit_not_in_use_2_QA)
                ]:
                    if qa_value != "-":
                        issues.append({
                            "KEY": key, "Tool": "Tool 1", "QA_By": qa_by,
                            "Question_Label": qa_field,
                            "Issue": "If option 3 is selected, all QA fields must have '-' value.",
                            "Choice": qa_value
                        })

            classroom_kit_feedback = str(row.get("classroom_kit_feedback", "")).strip()
            classroom_kit_feedback_other = str(row.get("classroom_kit_feedback_other", "")).strip()
            if "8888" in str(classroom_kit_feedback).split():
                if not classroom_kit_feedback_other or not is_english_text_strict(classroom_kit_feedback_other):
                    issues.append({
                        "KEY": key,
                        "Tool": "Tool 1",
                        "QA_By": qa_by,
                        "Question_Label": "classroom_kit_feedback_other",
                        "Issue": "If 'Other (8888)' is selected in feedback, classroom_kit_feedback_other must not be blank and must not contain Persian/Dari or Pashto letters.",
                        "Choice": classroom_kit_feedback_other
                    })

            teacher_kit_received = row.get("teacher_kit_received", "")
            teacher_kit_not_received_reason = row.get("teacher_kit_not_received_reason", "")
            teacher_kit_not_received_reason_other = row.get("teacher_kit_not_received_reason_other", "")
            teacher_kit_expected = row.get("teacher_kit_expected", "")
            teacher_kit_received_count = row.get("teacher_kit_received_count", "")
            teacher_material_included = row.get("teacher_material_included", "")
            teacher_material_included_other = row.get("teacher_material_included_other", "")
            teacher_materials_count = row.get("teacher_materials_count", "")
            teacher_kit_grouped_photo = row.get("teacher_kit_grouped_photo", "")
            teacher_kit_in_use_1 = row.get("teacher_kit_in_use_1", "")
            teacher_kit_in_use_1_QA = row.get("teacher_kit_in_use_1_QA", "")
            teacher_kit_in_use_2 = row.get("teacher_kit_in_use_2", "")
            teacher_kit_in_use_2_QA = row.get("teacher_kit_in_use_2_QA", "")
            teacher_kit_not_in_use_1 = row.get("teacher_kit_not_in_use_1", "")
            teacher_kit_not_in_use_1_QA = row.get("teacher_kit_not_in_use_1_QA", "")
            teacher_kit_not_in_use_2 = row.get("teacher_kit_not_in_use_2", "")
            teacher_kit_not_in_use_2_QA = row.get("teacher_kit_not_in_use_2_QA", "")
            teacher_kit_feedback = row.get("teacher_kit_feedback", "")
            teacher_kit_feedback_other = row.get("teacher_kit_feedback_other", "")

            if teacher_kit_received == "1":
                if teacher_kit_not_received_reason or teacher_kit_not_received_reason_other or teacher_kit_expected:
                    issues.append({
                        "KEY": key, "Tool": "Tool 1", "QA_By": qa_by,
                        "Question_Label": "teacher_kit_received",
                        "Issue": "If teacher_kit_received = 1, then related 'not received' questions must be blank.",
                        "Choice": teacher_kit_received
                    })
                if not teacher_kit_received_count or not teacher_material_included or not teacher_kit_grouped_photo:
                    issues.append({
                        "KEY": key, "Tool": "Tool 1", "QA_By": qa_by,
                        "Question_Label": "teacher_kit_received",
                        "Issue": "If teacher_kit_received = 1, then count, materials, and grouped photo must not be blank.",
                        "Choice": teacher_kit_received
                    })

            if teacher_kit_received_count.isdigit():
                if int(teacher_kit_received_count) == 0 or int(teacher_kit_received_count) > 3:
                    issues.append({
                        "KEY": key, "Tool": "Tool 1", "QA_By": qa_by,
                        "Question_Label": "teacher_kit_received_count",
                        "Issue": "Teacher kit must be between 1 and 3 per year.",
                        "Choice": teacher_kit_received_count
                    })

            if "8888" in str(teacher_material_included).split():
                if not teacher_material_included_other or not is_english_text(teacher_material_included_other):
                    issues.append({
                        "KEY": key, "Tool": "Tool 1", "QA_By": qa_by,
                        "Question_Label": "teacher_material_included_other",
                        "Issue": "If 'Other (8888)' is selected, then 'teacher_material_included_other' must not be blank or non-English.",
                        "Choice": teacher_material_included_other
                    })

            if teacher_material_included:
                included_count = len(str(teacher_material_included).split())
                if teacher_materials_count.isdigit() and int(teacher_materials_count) != included_count:
                    issues.append({
                        "KEY": key, "Tool": "Tool 1", "QA_By": qa_by,
                        "Question_Label": "teacher_materials_count",
                        "Issue": "Mismatch between teacher_materials_count and number of selected choices.",
                        "Choice": teacher_materials_count
                    })

            valid_photo_choices = ["Blur/Not Visible Photo", "Relevant Photo", "Irrelevant Photo"]

            if teacher_kit_grouped_photo == "1" and not teacher_kit_in_use_1:
                issues.append({
                    "KEY": key, "Tool": "Tool 1", "QA_By": qa_by,
                    "Question_Label": "teacher_kit_in_use_1",
                    "Issue": "If grouped photo = 1, then teacher_kit_in_use_1 must not be blank.",
                    "Choice": teacher_kit_in_use_1
                })

            if teacher_kit_in_use_1:
                if teacher_kit_in_use_1_QA not in valid_photo_choices:
                    issues.append({
                        "KEY": key, "Tool": "Tool 1", "QA_By": qa_by,
                        "Question_Label": "teacher_kit_in_use_1_QA",
                        "Issue": "Invalid QA choice for teacher_kit_in_use_1.",
                        "Choice": teacher_kit_in_use_1_QA
                    })

            if teacher_kit_in_use_2:
                if teacher_kit_in_use_2_QA not in valid_photo_choices:
                    issues.append({
                        "KEY": key, "Tool": "Tool 1", "QA_By": qa_by,
                        "Question_Label": "teacher_kit_in_use_2_QA",
                        "Issue": "Invalid QA choice for teacher_kit_in_use_2.",
                        "Choice": teacher_kit_in_use_2_QA
                    })

            if teacher_kit_grouped_photo == "2" and not teacher_kit_not_in_use_1:
                issues.append({
                    "KEY": key, "Tool": "Tool 1", "QA_By": qa_by,
                    "Question_Label": "teacher_kit_not_in_use_1",
                    "Issue": "If grouped photo = 2, then teacher_kit_not_in_use_1 must not be blank.",
                    "Choice": teacher_kit_not_in_use_1
                })

            if teacher_kit_not_in_use_1 and teacher_kit_not_in_use_1_QA not in valid_photo_choices:
                issues.append({
                    "KEY": key, "Tool": "Tool 1", "QA_By": qa_by,
                    "Question_Label": "teacher_kit_not_in_use_1_QA",
                    "Issue": "Invalid QA choice for teacher_kit_not_in_use_1.",
                    "Choice": teacher_kit_not_in_use_1_QA
                })

            if teacher_kit_not_in_use_2 and teacher_kit_not_in_use_2_QA not in valid_photo_choices:
                issues.append({
                    "KEY": key, "Tool": "Tool 1", "QA_By": qa_by,
                    "Question_Label": "teacher_kit_not_in_use_2_QA",
                    "Issue": "Invalid QA choice for teacher_kit_not_in_use_2.",
                    "Choice": teacher_kit_not_in_use_2_QA
                })

            if "8888" in str(teacher_kit_feedback).split():
                if not teacher_kit_feedback_other or not is_english_text(teacher_kit_feedback_other):
                    issues.append({
                        "KEY": key, "Tool": "Tool 1", "QA_By": qa_by,
                        "Question_Label": "teacher_kit_feedback_other",
                        "Issue": "If 'Other (8888)' is selected in feedback, then 'teacher_kit_feedback_other' must not be blank or non-English.",
                        "Choice": teacher_kit_feedback_other
                    })

            student_kit_received = row.get("student_kit_received", "")
            student_kit_received_count = row.get("student_kit_received_count", "")
            student_material_included = row.get("student_material_included", "")
            student_material_included_other = row.get("student_material_included_other", "")
            student_materials_count = row.get("student_materials_count", "")
            student_kit_grouped_photo = row.get("student_kit_grouped_photo", "")
            student_kit_in_use_1 = row.get("student_kit_in_use_1", "")
            student_kit_in_use_1_QA = row.get("student_kit_in_use_1_QA", "")
            student_kit_in_use_2 = row.get("student_kit_in_use_2", "")
            student_kit_in_use_2_QA = row.get("student_kit_in_use_2_QA", "")
            student_kit_not_in_use_1 = row.get("student_kit_not_in_use_1", "")
            student_kit_not_in_use_1_QA = row.get("student_kit_not_in_use_1_QA", "")
            student_kit_not_in_use_2 = row.get("student_kit_not_in_use_2", "")
            student_kit_not_in_use_2_QA = row.get("student_kit_not_in_use_2_QA", "")

            tlm_receipt_evidence = str(row.get("tlm_receipt_evidence", "")).strip()
            tlm_receipt_evidence_photo = str(row.get("tlm_receipt_evidence_photo", "")).strip()
            tlm_receipt_evidence_photo_QA = str(row.get("tlm_receipt_evidence_photo_QA", "")).strip()
            if tlm_receipt_evidence_photo:
                if not tlm_receipt_evidence_photo_QA or tlm_receipt_evidence_photo_QA == "-" or tlm_receipt_evidence_photo_QA not in ["Blur/Not Visible Photo", "Relevant Photo", "Irrelevant Photo"]:
                    issues.append({
                        "KEY": key, "Tool": "Tool 1", "QA_By": qa_by,
                        "Question_Label": "tlm_receipt_evidence_photo_QA",
                        "Issue": "If photo provided, tlm_receipt_evidence_photo_QA must be one of: Blur/Not Visible Photo, Relevant Photo, Irrelevant Photo.",
                        "Choice": tlm_receipt_evidence_photo_QA
                    })

            tlm_stock_evidence = str(row.get("tlm_stock_evidence", "")).strip()
            tlm_stock_evidence_photo = str(row.get("tlm_stock_evidence_photo", "")).strip()
            tlm_stock_evidence_photo_QA = str(row.get("tlm_stock_evidence_photo_QA", "")).strip()
            if tlm_stock_evidence == "1" and not tlm_stock_evidence_photo:
                issues.append({
                    "KEY": key, "Tool": "Tool 1", "QA_By": qa_by,
                    "Question_Label": "tlm_stock_evidence_photo",
                    "Issue": "If tlm_stock_evidence=1, tlm_stock_evidence_photo must not be blank.",
                    "Choice": tlm_stock_evidence_photo
                })
            if tlm_stock_evidence_photo:
                if not tlm_stock_evidence_photo_QA or tlm_stock_evidence_photo_QA == "-" or tlm_stock_evidence_photo_QA not in ["Blur/Not Visible Photo", "Relevant Photo", "Irrelevant Photo"]:
                    issues.append({
                        "KEY": key, "Tool": "Tool 1", "QA_By": qa_by,
                        "Question_Label": "tlm_stock_evidence_photo_QA",
                        "Issue": "If photo provided, tlm_stock_evidence_photo_QA must be valid.",
                        "Choice": tlm_stock_evidence_photo_QA
                    })

            resp_title = str(row.get("Resp_title", "")).strip()
            salary_paid_regularly = str(row.get("salary_paid_regularly", "")).strip()
            paid_past_two_months = str(row.get("paid_past_two_months", "")).strip()
            last_paid_month = str(row.get("last_paid_month", "")).strip()
            salary_payment_type = str(row.get("salary_payment_type", "")).strip()
            partial_salary_reason = str(row.get("partial_salary_reason", "")).strip()

            if resp_title == "1" and not salary_paid_regularly:
                issues.append({
                    "KEY": key, "Tool": "Tool 1", "QA_By": qa_by,
                    "Question_Label": "salary_paid_regularly",
                    "Issue": "If Resp_title=1, salary_paid_regularly must be answered.",
                    "Choice": salary_paid_regularly
                })
            if salary_paid_regularly and not paid_past_two_months:
                issues.append({
                    "KEY": key, "Tool": "Tool 1", "QA_By": qa_by,
                    "Question_Label": "paid_past_two_months",
                    "Issue": "If salary_paid_regularly answered, paid_past_two_months must not be blank.",
                    "Choice": paid_past_two_months
                })
            if paid_past_two_months == "0" and not last_paid_month:
                issues.append({
                    "KEY": key, "Tool": "Tool 1", "QA_By": qa_by,
                    "Question_Label": "last_paid_month",
                    "Issue": "If paid_past_two_months=0, last_paid_month must not be blank.",
                    "Choice": last_paid_month
                })
            if "8888" in last_paid_month and (not last_paid_month or not is_english_text_strict(last_paid_month)):
                issues.append({
                    "KEY": key, "Tool": "Tool 1", "QA_By": qa_by,
                    "Question_Label": "last_paid_month",
                    "Issue": "If last_paid_month=8888, it must not be blank or non-English.",
                    "Choice": last_paid_month
                })
            if salary_payment_type in ["2", "3"] and not partial_salary_reason:
                issues.append({
                    "KEY": key, "Tool": "Tool 1", "QA_By": qa_by,
                    "Question_Label": "partial_salary_reason",
                    "Issue": "If salary_payment_type=2 or 3, partial_salary_reason must not be blank.",
                    "Choice": partial_salary_reason
                })

            ip_support_activities = str(row.get("ip_support_activities", "")).strip()
            if not ip_support_activities:
                issues.append({
                    "KEY": key, "Tool": "Tool 1", "QA_By": qa_by,
                    "Question_Label": "ip_support_activities",
                    "Issue": "ip_support_activities must not be blank.",
                    "Choice": ip_support_activities
                })

            ip_visit_frequency = str(row.get("ip_visit_frequency", "")).strip()
            ip_visit_frequency_other = str(row.get("ip_visit_frequency_other", "")).strip()
            if "8888" in ip_visit_frequency and (not ip_visit_frequency_other or not is_english_text_strict(ip_visit_frequency_other)):
                issues.append({
                    "KEY": key, "Tool": "Tool 1", "QA_By": qa_by,
                    "Question_Label": "ip_visit_frequency_other",
                    "Issue": "If 8888 selected, ip_visit_frequency_other must not be blank or non-English.",
                    "Choice": ip_visit_frequency_other
                })

            ip_trainings = str(row.get("ip_trainings", "")).strip()
            ip_trainings_other = str(row.get("ip_trainings_other", "")).strip()
            ip_training_timing = str(row.get("ip_training_timing", "")).strip()
            if "8888" in ip_trainings and (not ip_trainings_other or not is_english_text_strict(ip_trainings_other)):
                issues.append({
                    "KEY": key, "Tool": "Tool 1", "QA_By": qa_by,
                    "Question_Label": "ip_trainings_other",
                    "Issue": "If 8888 selected, ip_trainings_other must not be blank or non-English.",
                    "Choice": ip_trainings_other
                })

            if ip_trainings in ["0", "9999", "7777"]:
                if ip_training_timing:
                    issues.append({
                        "KEY": key, "Tool": "Tool 1", "QA_By": qa_by,
                        "Question_Label": "ip_training_timing",
                        "Issue": "If ip_trainings is 0, 9999, or 7777, then ip_training_timing must be blank.",
                        "Choice": ip_training_timing
                    })
            else:
                if not ip_training_timing:
                    issues.append({
                        "KEY": key, "Tool": "Tool 1", "QA_By": qa_by,
                        "Question_Label": "ip_training_timing",
                        "Issue": "If ip_trainings is not 0/9999/7777, then ip_training_timing must not be blank.",
                        "Choice": ip_training_timing
                    })

            unicef_visit_frequency = str(row.get("unicef_visit_frequency", "")).strip()
            unicef_visit_frequency_other = str(row.get("unicef_visit_frequency_other", "")).strip()
            if "8888" in unicef_visit_frequency and (not unicef_visit_frequency_other or not is_english_text_strict(unicef_visit_frequency_other)):
                issues.append({
                    "KEY": key, "Tool": "Tool 1", "QA_By": qa_by,
                    "Question_Label": "unicef_visit_frequency_other",
                    "Issue": "If 8888 selected, unicef_visit_frequency_other must not be blank or non-English.",
                    "Choice": unicef_visit_frequency_other
                })

            has_complaint_box = str(row.get("has_complaint_box", "")).strip()
            grm_complaint_box_photo = str(row.get("grm_complaint_box_photo", "")).strip()
            grm_complaint_box_photo_QA = str(row.get("grm_complaint_box_photo_QA", "")).strip()
            grm_complaint_box_visibility = str(row.get("grm_complaint_box_visibility", "")).strip()

            if has_complaint_box == "1":
                if not grm_complaint_box_photo or not grm_complaint_box_photo_QA or not grm_complaint_box_visibility:
                    issues.append({
                        "KEY": key, "Tool": "Tool 1", "QA_By": qa_by,
                        "Question_Label": "has_complaint_box",
                        "Issue": "If has_complaint_box=1, photo, QA, and visibility must not be blank.",
                        "Choice": f"{grm_complaint_box_photo}, {grm_complaint_box_photo_QA}, {grm_complaint_box_visibility}"
                    })
            if grm_complaint_box_photo:
                if not grm_complaint_box_photo_QA or grm_complaint_box_photo_QA == "-" or grm_complaint_box_photo_QA not in ["Blur/Not Visible Photo", "Relevant Photo", "Irrelevant Photo"]:
                    issues.append({
                        "KEY": key, "Tool": "Tool 1", "QA_By": qa_by,
                        "Question_Label": "grm_complaint_box_photo_QA",
                        "Issue": "If photo provided, QA must be one of: Blur/Not Visible Photo, Relevant Photo, Irrelevant Photo.",
                        "Choice": grm_complaint_box_photo_QA
                    })

            no_grm_available = str(row.get("no_grm_available", "")).strip()
            no_grm_reason = str(row.get("no_grm_reason", "")).strip()
            no_grm_reason_other = str(row.get("no_grm_reason_other", "")).strip()

            if no_grm_available == "1":
                if not no_grm_reason:
                    issues.append({
                        "KEY": key, "Tool": "Tool 1", "QA_By": qa_by,
                        "Question_Label": "no_grm_reason",
                        "Issue": "When no_grm_available=1, no_grm_reason must not be blank.",
                        "Choice": no_grm_reason
                    })

            if "8888" in [c.strip() for c in no_grm_reason.split(",") if c.strip()]:
                if not no_grm_reason_other or not is_english_text_strict(no_grm_reason_other):
                    issues.append({
                        "KEY": key, "Tool": "Tool 1", "QA_By": qa_by,
                        "Question_Label": "no_grm_reason_other",
                        "Issue": "If no_grm_reason includes 8888, no_grm_reason_other must not be blank and must be in English.",
                        "Choice": no_grm_reason_other
                    })

            conflict_resolution_methods = str(row.get("conflict_resolution_methods", "")).strip()
            conflict_resolution_methods_other = str(row.get("conflict_resolution_methods_other", "")).strip()

            if not conflict_resolution_methods:
                issues.append({
                    "KEY": key, "Tool": "Tool 1", "QA_By": qa_by,
                    "Question_Label": "conflict_resolution_methods",
                    "Issue": "conflict_resolution_methods must not be blank.",
                    "Choice": conflict_resolution_methods
                })
            else:
                if "8888" in [c.strip() for c in conflict_resolution_methods.split(",") if c.strip()]:
                    if not conflict_resolution_methods_other or not is_english_text_strict(conflict_resolution_methods_other):
                        issues.append({
                            "KEY": key, "Tool": "Tool 1", "QA_By": qa_by,
                            "Question_Label": "conflict_resolution_methods_other",
                            "Issue": "If conflict_resolution_methods includes 8888, conflict_resolution_methods_other must not be blank and must be in English.",
                            "Choice": conflict_resolution_methods_other
                        })

            grm_training_received = str(row.get("grm_training_received", "")).strip()
            grm_training_topics = str(row.get("grm_training_topics", "")).strip()
            grm_training_timing = str(row.get("grm_training_timing", "")).strip()
            no_grm_training_reason = str(row.get("no_grm_training_reason", "")).strip()
            no_grm_training_reason_other = str(row.get("no_grm_training_reason_other", "")).strip()

            if grm_training_received in ["0", "9999", "7777"]:
                for fld in ["grm_training_topics", "grm_training_timing"]:
                    if str(row.get(fld, "")).strip():
                        issues.append({
                            "KEY": key, "Tool": "Tool 1", "QA_By": qa_by,
                            "Question_Label": fld,
                            "Issue": f"{fld} must be blank when grm_training_received is 0/9999/7777.",
                            "Choice": row.get(fld, "")
                        })
            elif grm_training_received == "1":
                        if no_grm_training_reason:  # اگر no_grm_training_reason خالی نباشد
                            issues.append({
                                "KEY": key,
                                "Tool": "Tool 1",
                                "QA_By": qa_by,
                                "Question_Label": "no_grm_training_reason",
                                "Issue": "When grm_training_received=1, no_grm_training_reason must be blank.",
                                "Choice": no_grm_training_reason
                            })

            if "8888" in [c.strip() for c in no_grm_training_reason.split(",") if c.strip()]:
                if not no_grm_training_reason_other or not is_english_text_strict(no_grm_training_reason_other):
                    issues.append({
                        "KEY": key, "Tool": "Tool 1", "QA_By": qa_by,
                        "Question_Label": "no_grm_training_reason_other",
                        "Issue": "If no_grm_training_reason includes 8888, other must not be blank and must be in English.",
                        "Choice": no_grm_training_reason_other
                    })

            complaint_made = str(row.get("complaint_made", "")).strip()
            complaint_resolved = str(row.get("complaint_resolved", "")).strip()
            complaint_resolution_time = str(row.get("complaint_resolution_time", "")).strip()
            complaint_resolution_satisfaction = str(row.get("complaint_resolution_satisfaction", "")).strip()
            complaint_resolution_dissatisfaction_reason = str(row.get("complaint_resolution_dissatisfaction_reason", "")).strip()
            complaint_resolution_dissatisfaction_reason_other = str(row.get("complaint_resolution_dissatisfaction_reason_other", "")).strip()

            if complaint_made in ["0", "7777"]:
                for fld in ["complaint_resolved", "complaint_resolution_time", "complaint_resolution_satisfaction",
                            "complaint_resolution_dissatisfaction_reason",
                            "complaint_resolution_dissatisfaction_reason_other"]:
                    if str(row.get(fld, "")).strip():
                        issues.append({
                            "KEY": key, "Tool": "Tool 1", "QA_By": qa_by,
                            "Question_Label": fld,
                            "Issue": f"{fld} must be blank when complaint_made is 0 or 7777.",
                            "Choice": row.get(fld, "")
                        })

            if complaint_made == "1":
                if not complaint_resolved:
                    issues.append({
                        "KEY": key, "Tool": "Tool 1", "QA_By": qa_by,
                        "Question_Label": "complaint_resolved",
                        "Issue": "When complaint_made=1, complaint_resolved must not be blank.",
                        "Choice": complaint_resolved
                    })

            if complaint_resolved == "1":
                for fld in ["complaint_resolution_time", "complaint_resolution_satisfaction"]:
                    if not str(row.get(fld, "")).strip():
                        issues.append({
                            "KEY": key, "Tool": "Tool 1", "QA_By": qa_by,
                            "Question_Label": fld,
                            "Issue": f"{fld} must not be blank when complaint_resolved=1.",
                            "Choice": row.get(fld, "")
                        })

            if complaint_resolution_satisfaction == "0":
                if not complaint_resolution_dissatisfaction_reason:
                    issues.append({
                        "KEY": key, "Tool": "Tool 1", "QA_By": qa_by,
                        "Question_Label": "complaint_resolution_dissatisfaction_reason",
                        "Issue": "When complaint_resolution_satisfaction=0, complaint_resolution_dissatisfaction_reason must not be blank.",
                        "Choice": complaint_resolution_dissatisfaction_reason
                    })

            if "8888" in [c.strip() for c in complaint_resolution_dissatisfaction_reason.split(",") if c.strip()]:
                if not complaint_resolution_dissatisfaction_reason_other or not is_english_text_strict(complaint_resolution_dissatisfaction_reason_other):
                    issues.append({
                        "KEY": key, "Tool": "Tool 1", "QA_By": qa_by,
                        "Question_Label": "complaint_resolution_dissatisfaction_reason_other",
                        "Issue": "If complaint_resolution_dissatisfaction_reason includes 8888, other must not be blank and must be in English.",
                        "Choice": complaint_resolution_dissatisfaction_reason_other
                    })

            coc_awareness = str(row.get("coc_awareness", "")).strip()
            coc_signed = str(row.get("coc_signed", "")).strip()
            coc_signed_timing = str(row.get("coc_signed_timing", "")).strip()
            coc_training = str(row.get("coc_training", "")).strip()
            coc_training_timing = str(row.get("coc_training_timing", "")).strip()
            coc_principles = str(row.get("coc_principles", "")).strip()
            coc_principles_count = str(row.get("coc_principles_count", "")).strip()

            if coc_awareness == "1":
                if not coc_signed:
                    issues.append({
                        "KEY": key, "Tool": "Tool 1", "QA_By": qa_by,
                        "Question_Label": "coc_signed",
                        "Issue": "When coc_awareness=1, coc_signed must not be blank.",
                        "Choice": coc_signed
                    })


            # ======================
            # New Conditions for CoC Awareness, Signed, Training
            # ======================

            # 1) coc_awareness → if choice == 1 then coc_signed must NOT be blank
            if "1" in str(row.get("coc_awareness", "")):
                if not str(row.get("coc_signed", "")).strip():
                    issues.append({
                        "KEY": key, "Tool": "Tool 1", "QA_By": qa_by,
                        "Question_Label": "coc_signed",
                        "Issue": "If coc_awareness = 1, then coc_signed must not be blank.",
                        "Choice": row.get("coc_signed", "")
                    })
            # ======================
            # New Condition for coc_training = 0
            # ======================

            if "0" in str(row.get("coc_training", "")):
                if str(row.get("coc_training_timing", "")).strip():
                    issues.append({
                        "KEY": key, "Tool": "Tool 1", "QA_By": qa_by,
                        "Question_Label": "coc_training_timing",
                        "Issue": "If coc_training = 0, then coc_training_timing must be blank.",
                        "Choice": row.get("coc_training_timing", "")
                    })

            # 2) coc_signed → if choice == 1 then coc_signed_timing must NOT be blank
            if "1" in str(row.get("coc_signed", "")):
                if not str(row.get("coc_signed_timing", "")).strip():
                    issues.append({
                        "KEY": key, "Tool": "Tool 1", "QA_By": qa_by,
                        "Question_Label": "coc_signed_timing",
                        "Issue": "If coc_signed = 1, then coc_signed_timing must not be blank.",
                        "Choice": row.get("coc_signed_timing", "")
                    })

            # 3) coc_training → if choice == 1 then coc_training_timing must NOT be blank
            if "1" in str(row.get("coc_training", "")):
                if not str(row.get("coc_training_timing", "")).strip():
                    issues.append({
                        "KEY": key, "Tool": "Tool 1", "QA_By": qa_by,
                        "Question_Label": "coc_training_timing",
                        "Issue": "If coc_training = 1, then coc_training_timing must not be blank.",
                        "Choice": row.get("coc_training_timing", "")
                    })

            if coc_awareness in ["0", "7777"] and str(coc_principles).strip():
                issues.append({
                    "KEY": key, "Tool": "Tool 1", "QA_By": qa_by,
                    "Question_Label": "coc_principles",
                    "Issue": "coc_principles must be blank when coc_awareness is 0 or 7777.",
                    "Choice": coc_principles
                })
            # شرط coc_principles_count فقط وقتی که coc_principles شامل 1 باشه
            if "1" in str(coc_principles).split():
                if str(coc_principles_count).strip():
                    try:
                        count_choices = len(str(coc_principles).split())
                        if int(coc_principles_count) != count_choices:
                            issues.append({
                                "KEY": key, "Tool": "Tool 1", "QA_By": qa_by,
                                "Question_Label": "coc_principles_count",
                                "Issue": "coc_principles_count must equal the number of selected choices in coc_principles.",
                                "Choice": coc_principles_count
                            })
                    except Exception:
                        issues.append({
                            "KEY": key, "Tool": "Tool 1", "QA_By": qa_by,
                            "Question_Label": "coc_principles_count",
                            "Issue": "coc_principles_count check failed (non-numeric or parsing error).",
                            "Choice": coc_principles_count
                        })

            gbv_hotline_visible = str(row.get("gbv_hotline_visible", "")).strip()
            gbv_hotline_photo = str(row.get("gbv_hotline_photo", "")).strip()
            gbv_hotline_photo_QA = str(row.get("gbv_hotline_photo_QA", "")).strip()
            valid_photo_choices = ["Blur/Not Visible Photo", "Relevant Photo", "Irrelevant Photo"]

            if not gbv_hotline_visible:
                issues.append({
                    "KEY": key, "Tool": "Tool 1", "QA_By": qa_by,
                    "Question_Label": "gbv_hotline_visible",
                    "Issue": "gbv_hotline_visible must not be blank.",
                    "Choice": gbv_hotline_visible
                })
            else:
                if gbv_hotline_visible == "0":
                    if gbv_hotline_photo:
                        issues.append({
                            "KEY": key, "Tool": "Tool 1", "QA_By": qa_by,
                            "Question_Label": "gbv_hotline_photo",
                            "Issue": "When gbv_hotline_visible=0, gbv_hotline_photo must be blank.",
                            "Choice": gbv_hotline_photo
                        })
                    if gbv_hotline_photo_QA not in ["", "-"]:
                        issues.append({
                            "KEY": key, "Tool": "Tool 1", "QA_By": qa_by,
                            "Question_Label": "gbv_hotline_photo_QA",
                            "Issue": "When gbv_hotline_visible=0, gbv_hotline_photo_QA must be blank or '-'.",
                            "Choice": gbv_hotline_photo_QA
                        })
                if gbv_hotline_visible == "1":
                    if not gbv_hotline_photo:
                        issues.append({
                            "KEY": key, "Tool": "Tool 1", "QA_By": qa_by,
                            "Question_Label": "gbv_hotline_photo",
                            "Issue": "When gbv_hotline_visible=1, gbv_hotline_photo must not be blank.",
                            "Choice": gbv_hotline_photo
                        })

                if gbv_hotline_photo:
                    if not gbv_hotline_photo_QA or gbv_hotline_photo_QA == "-":
                        issues.append({
                            "KEY": key, "Tool": "Tool 1", "QA_By": qa_by,
                            "Question_Label": "gbv_hotline_photo_QA",
                            "Issue": "If gbv_hotline_photo provided, gbv_hotline_photo_QA must not be blank or '-'.",
                            "Choice": gbv_hotline_photo_QA
                        })
                    elif gbv_hotline_photo_QA not in valid_photo_choices:
                        issues.append({
                            "KEY": key, "Tool": "Tool 1", "QA_By": qa_by,
                            "Question_Label": "gbv_hotline_photo_QA",
                            "Issue": "gbv_hotline_photo_QA must be one of the allowed photo QA choices.",
                            "Choice": gbv_hotline_photo_QA
                        })

            grade_appropriate_textbooks = str(row.get("grade_appropriate_textbooks", "")).strip()
            language_appropriate_textbooks = str(row.get("language_appropriate_textbooks", "")).strip()
            latest_version_textbooks = str(row.get("latest_version_textbooks", "")).strip()
            same_version_textbooks = str(row.get("same_version_textbooks", "")).strip()

            curriculum_has_changed = str(row.get("curriculum_has_changed", "")).strip()
            curriculum_change_types = str(row.get("curriculum_change_types", "")).strip()
            curriculum_change_types_other = str(row.get("curriculum_change_types_other", "")).strip()

            removed_subjects = str(row.get("removed_subjects", "")).strip()
            added_subjects_count = str(row.get("added_subjects_count", "")).strip()
            added_subjects_known = str(row.get("added_subjects_known", "")).strip()
            added_subjects_repeat_count = str(row.get("added_subjects_repeat_count", "")).strip()

            modified_subjects_known = str(row.get("modified_subjects_known", "")).strip()
            modified_subjects_explanation = str(row.get("modified_subjects_explanation", "")).strip()
            modified_subjects_explanation_QA = str(row.get("modified_subjects_explanation_QA", "")).strip()

            more_changes = str(row.get("more_changes", "")).strip()
            more_changes_details = str(row.get("more_changes_details", "")).strip()
            more_changes_details_other = str(row.get("more_changes_details_other", "")).strip()

            book_comparison = str(row.get("book_comparison", "")).strip()
            book_modified = str(row.get("book_modified", "")).strip()
            book_modification_details = str(row.get("book_modification_details", "")).strip()
            book_modification_details_other = str(row.get("book_modification_details_other", "")).strip()

            book_replacement_details = str(row.get("book_replacement_details", "")).strip()
            book_replacement_details_other = str(row.get("book_replacement_details_other", "")).strip()

            quality_change = str(row.get("quality_change", "")).strip()
            improvement_details = str(row.get("improvement_details", "")).strip()
            improvement_details_other = str(row.get("improvement_details_other", "")).strip()

            if grade_appropriate_textbooks == "0":
                for q_name, q_value in [
                    ("language_appropriate_textbooks", language_appropriate_textbooks),
                    ("latest_version_textbooks", latest_version_textbooks),
                    ("same_version_textbooks", same_version_textbooks),
                ]:
                    if q_value != "":
                        issues.append({
                            "KEY": key, "Tool": "Tool 1", "QA_By": qa_by,
                            "Question_Label": q_name,
                            "Issue": "If grade_appropriate_textbooks=0 (No, none of them), this question must be blank.",
                            "Choice": q_value
                        })

            if latest_version_textbooks not in ("", "0", "1", "2"):
                issues.append({
                    "KEY": key, "Tool": "Tool 1", "QA_By": qa_by,
                    "Question_Label": "latest_version_textbooks",
                    "Issue": "latest_version_textbooks must only be 0, 1, 2 or blank (check codebook).",
                    "Choice": latest_version_textbooks
                })

            if grade_appropriate_textbooks in ("1", "2") and same_version_textbooks == "":
                issues.append({
                    "KEY": key, "Tool": "Tool 1", "QA_By": qa_by,
                    "Question_Label": "same_version_textbooks",
                    "Issue": "same_version_textbooks cannot be blank when grade_appropriate_textbooks is 1 or 2.",
                    "Choice": same_version_textbooks
                })

            if curriculum_has_changed not in ("", "0", "1", "9999", "7777"):
                issues.append({
                    "KEY": key, "Tool": "Tool 1", "QA_By": qa_by,
                    "Question_Label": "curriculum_has_changed",
                    "Issue": "curriculum_has_changed must be 0,1,9999,7777 or blank (check codebook).",
                    "Choice": curriculum_has_changed
                })

            change_types_list = parse_choices(curriculum_change_types)
            if curriculum_has_changed == "1":
                if not change_types_list:
                    issues.append({
                        "KEY": key, "Tool": "Tool 1", "QA_By": qa_by,
                        "Question_Label": "curriculum_change_types",
                        "Issue": "If curriculum_has_changed=1, curriculum_change_types must not be blank.",
                        "Choice": curriculum_change_types
                    })
                else:
                    allowed_ct = {"1", "2", "3", "9999", "8888"}
                    if not all(c in allowed_ct for c in change_types_list):
                        issues.append({
                            "KEY": key, "Tool": "Tool 1", "QA_By": qa_by,
                            "Question_Label": "curriculum_change_types",
                            "Issue": "curriculum_change_types contains values outside allowed set (1,2,3,9999,8888).",
                            "Choice": curriculum_change_types
                        })

            if "8888" in change_types_list:
                if not curriculum_change_types_other or not is_english_text_strict(curriculum_change_types_other):
                    issues.append({
                        "KEY": key, "Tool": "Tool 1", "QA_By": qa_by,
                        "Question_Label": "curriculum_change_types_other",
                        "Issue": "If curriculum_change_types includes 8888, curriculum_change_types_other must be English and not blank.",
                        "Choice": curriculum_change_types_other
                    })
            else:
                if curriculum_change_types_other:
                    issues.append({
                        "KEY": key, "Tool": "Tool 1", "QA_By": qa_by,
                        "Question_Label": "curriculum_change_types_other",
                        "Issue": "curriculum_change_types_other must be blank unless 8888 is selected in curriculum_change_types.",
                        "Choice": curriculum_change_types_other
                    })

            if "1" in change_types_list and not removed_subjects:
                issues.append({
                    "KEY": key, "Tool": "Tool 1", "QA_By": qa_by,
                    "Question_Label": "removed_subjects",
                    "Issue": "removed_subjects cannot be blank if curriculum_change_types includes 1.",
                    "Choice": removed_subjects
                })

            if "2" in change_types_list:
                for q_name, q_value in [
                    ("added_subjects_count", added_subjects_count),
                    ("added_subjects_known", added_subjects_known),
                    ("added_subjects_repeat_count", added_subjects_repeat_count),
                ]:
                    if not q_value:
                        issues.append({
                            "KEY": key, "Tool": "Tool 1", "QA_By": qa_by,
                            "Question_Label": q_name,
                            "Issue": f"{q_name} cannot be blank if curriculum_change_types includes 2.",
                            "Choice": q_value
                        })

            if "3" in change_types_list and not modified_subjects_known:
                issues.append({
                    "KEY": key, "Tool": "Tool 1", "QA_By": qa_by,
                    "Question_Label": "modified_subjects_known",
                    "Issue": "modified_subjects_known cannot be blank if curriculum_change_types includes 3.",
                    "Choice": modified_subjects_known
                })

            if modified_subjects_known == "1" and not modified_subjects_explanation:
                issues.append({
                    "KEY": key, "Tool": "Tool 1", "QA_By": qa_by,
                    "Question_Label": "modified_subjects_explanation",
                    "Issue": "If modified_subjects_known=1, modified_subjects_explanation must not be blank.",
                    "Choice": modified_subjects_explanation
                })

            if modified_subjects_explanation:
                if not modified_subjects_explanation_QA or modified_subjects_explanation_QA.strip() == "-":
                    issues.append({
                        "KEY": key, "Tool": "Tool 1", "QA_By": qa_by,
                        "Question_Label": "modified_subjects_explanation_QA",
                        "Issue": "If modified_subjects_explanation has value, modified_subjects_explanation_QA must not be blank or '-'.",
                        "Choice": modified_subjects_explanation_QA
                    })

            if curriculum_has_changed in ("1") and not more_changes:
                issues.append({
                    "KEY": key, "Tool": "Tool 1", "QA_By": qa_by,
                    "Question_Label": "more_changes",
                    "Issue": "If curriculum_has_changed is 0 or 9999, more_changes must not be blank.",
                    "Choice": more_changes
                })

            more_changes_list = parse_choices(more_changes)
            if "1" in more_changes_list and not more_changes_details:
                issues.append({
                    "KEY": key, "Tool": "Tool 1", "QA_By": qa_by,
                    "Question_Label": "more_changes_details",
                    "Issue": "If more_changes includes 1, more_changes_details cannot be blank.",
                    "Choice": more_changes_details
                })

            if "8888" in parse_choices(more_changes_details) and (not more_changes_details_other or not is_english_text_strict(more_changes_details_other)):
                issues.append({
                    "KEY": key, "Tool": "Tool 1", "QA_By": qa_by,
                    "Question_Label": "more_changes_details_other",
                    "Issue": "If more_changes_details includes 8888, more_changes_details_other must be English and not blank.",
                    "Choice": more_changes_details_other
                })

            if not book_comparison:
                issues.append({
                    "KEY": key, "Tool": "Tool 1", "QA_By": qa_by,
                    "Question_Label": "book_comparison",
                    "Issue": "book_comparison cannot be blank.",
                    "Choice": book_comparison
                })

            if book_comparison in ("1", "2") and not book_modified:
                issues.append({
                    "KEY": key, "Tool": "Tool 1", "QA_By": qa_by,
                    "Question_Label": "book_modified",
                    "Issue": "If book_comparison=1 or 2, book_modified must not be blank.",
                    "Choice": book_modified
                })

            if "8888" in parse_choices(book_modification_details) and (not book_modification_details_other or not is_english_text_strict(book_modification_details_other)):
                issues.append({
                    "KEY": key, "Tool": "Tool 1", "QA_By": qa_by,
                    "Question_Label": "book_modification_details_other",
                    "Issue": "If book_modification_details includes 8888, book_modification_details_other must be English and not blank.",
                    "Choice": book_modification_details_other
                })

            if book_comparison == "3" and not book_replacement_details:
                issues.append({
                    "KEY": key, "Tool": "Tool 1", "QA_By": qa_by,
                    "Question_Label": "book_replacement_details",
                    "Issue": "If book_comparison=3, book_replacement_details must not be blank.",
                    "Choice": book_replacement_details
                })

            if "8888" in parse_choices(book_replacement_details) and (not book_replacement_details_other or not is_english_text_strict(book_replacement_details_other)):
                issues.append({
                    "KEY": key, "Tool": "Tool 1", "QA_By": qa_by,
                    "Question_Label": "book_replacement_details_other",
                    "Issue": "If book_replacement_details includes 8888, book_replacement_details_other must be English and not blank.",
                    "Choice": book_replacement_details_other
                })

            if quality_change not in ("", "1", "2", "3", "9999", "7777"):
                issues.append({
                    "KEY": key, "Tool": "Tool 1", "QA_By": qa_by,
                    "Question_Label": "quality_change",
                    "Issue": "quality_change must only be 1,2,3,9999,7777 or blank.",
                    "Choice": quality_change
                })

            if quality_change == "1" and not improvement_details:
                issues.append({
                    "KEY": key, "Tool": "Tool 1", "QA_By": qa_by,
                    "Question_Label": "improvement_details",
                    "Issue": "If quality_change=1, improvement_details must not be blank.",
                    "Choice": improvement_details
                })

            if "8888" in parse_choices(improvement_details) and (not improvement_details_other or not is_english_text_strict(improvement_details_other)):
                issues.append({
                    "KEY": key, "Tool": "Tool 1", "QA_By": qa_by,
                    "Question_Label": "improvement_details_other",
                    "Issue": "If improvement_details includes 8888, improvement_details_other must be English and not blank.",
                    "Choice": improvement_details_other
                })

        quality_change = str(row.get("quality_change", "")).strip()
        worsening_details = str(row.get("worsening_details", "")).strip()
        if "2" in parse_choices(quality_change) and not worsening_details:
            issues.append({
                "KEY": key, "Tool": "Tool 1", "QA_By": qa_by,
                "Question_Label": "worsening_details",
                "Issue": "If quality_change includes 2, worsening_details must not be blank.",
                "Choice": worsening_details
            })

        worsening_details_other = str(row.get("worsening_details_other", "")).strip()
        if "8888" in parse_choices(worsening_details):
            if not worsening_details_other or not is_english_text_strict(worsening_details_other):
                issues.append({
                    "KEY": key, "Tool": "Tool 1", "QA_By": qa_by,
                    "Question_Label": "worsening_details_other",
                    "Issue": "If worsening_details includes 8888, worsening_details_other must not be blank and must be in English.",
                    "Choice": worsening_details_other
                })

        training_climate_change = str(row.get("Training_climate_change", "")).strip()
        if "1" in parse_choices(training_climate_change):
            required_fields = [
                "training_cc_causes_effects",
                "training_cc_vulnerables_impacts",
                "cc_understanding_risk_climate_hazards",
                "cc_understanding_adaptation_strategies",
                "cc_materials_relevance",
                "cc_teaching"
            ]
            for field in required_fields:
                field_value = str(row.get(field, "")).strip()
                if not field_value:
                    issues.append({
                        "KEY": key, "Tool": "Tool 1", "QA_By": qa_by,
                        "Question_Label": field,
                        "Issue": f"If Training_climate_change includes 1, {field} must not be blank.",
                        "Choice": field_value
                    })

        cc_teaching = str(row.get("cc_teaching", "")).strip()
        cc_teaching_topics = str(row.get("cc_teaching_topics", "")).strip()
        if "1" in parse_choices(cc_teaching) and not cc_teaching_topics:
            issues.append({
                "KEY": key, "Tool": "Tool 1", "QA_By": qa_by,
                "Question_Label": "cc_teaching_topics",
                "Issue": "If cc_teaching includes 1, cc_teaching_topics must not be blank.",
                "Choice": cc_teaching_topics
            })

        cc_teaching_topics_translation = str(row.get("cc_teaching_topics_Translation", "")).strip()
        if cc_teaching_topics:
            if not cc_teaching_topics_translation or cc_teaching_topics_translation in ["-",
                                                                                        ""] or not is_english_text_strict(
                    cc_teaching_topics_translation):
                issues.append({
                    "KEY": key, "Tool": "Tool 1", "QA_By": qa_by,
                    "Question_Label": "cc_teaching_topics_Translation",
                    "Issue": "If cc_teaching_topics has value, cc_teaching_topics_Translation must not be blank, '-' or non-English.",
                    "Choice": cc_teaching_topics_translation
                })

        if "1" in parse_choices(cc_teaching):
            method_fields = [
                "cc_teaching_use_visual_aids",
                "cc_teaching_use_local_examples",
                "cc_teaching_participatory_methods"
            ]
            for field in method_fields:
                field_value = str(row.get(field, "")).strip()
                if not field_value:
                    issues.append({
                        "KEY": key, "Tool": "Tool 1", "QA_By": qa_by,
                        "Question_Label": field,
                        "Issue": f"If cc_teaching includes 1, {field} must not be blank.",
                        "Choice": field_value
                    })
        cc_training_challenges = str(row.get("cc_training_challenges", "")).strip()
        cc_training_challenges_translation = str(row.get("cc_training_challenges_Translation", "")).strip()
        if cc_training_challenges:
            if not cc_training_challenges_translation or cc_training_challenges_translation in ["-",
                                                                                                ""] or not is_english_text_strict(
                    cc_training_challenges_translation):
                issues.append({
                    "KEY": key, "Tool": "Tool 1", "QA_By": qa_by,
                    "Question_Label": "cc_training_challenges_Translation",
                    "Issue": "If cc_training_challenges has value, cc_training_challenges_Translation must not be blank, '-' or non-English.",
                    "Choice": cc_training_challenges_translation
                })

        cc_training_suggestions = str(row.get("cc_training_suggestions", "")).strip()
        cc_training_suggestions_translation = str(row.get("cc_training_suggestions_Translation", "")).strip()
        if cc_training_suggestions:
            if not cc_training_suggestions_translation or cc_training_suggestions_translation in ["-",
                                                                                                  ""] or not is_english_text_strict(
                    cc_training_suggestions_translation):
                issues.append({
                    "KEY": key, "Tool": "Tool 1", "QA_By": qa_by,
                    "Question_Label": "cc_training_suggestions_Translation",
                    "Issue": "If cc_training_suggestions has value, cc_training_suggestions_Translation must not be blank, '-' or non-English.",
                    "Choice": cc_training_suggestions_translation
                })

        transition_planning_activities = str(row.get("transition_planning_activities", "")).strip()
        transition_activities_description = str(row.get("transition_activities_description", "")).strip()
        if "1" in parse_choices(transition_planning_activities) and not transition_activities_description:
            issues.append({
                "KEY": key, "Tool": "Tool 1", "QA_By": qa_by,
                "Question_Label": "transition_activities_description",
                "Issue": "If transition_planning_activities includes 1, transition_activities_description must not be blank.",
                "Choice": transition_activities_description
            })

        transition_activities_description_translation = str(
            row.get("transition_activities_description_Translation", "")).strip()
        if transition_activities_description:
            if not transition_activities_description_translation or transition_activities_description_translation in [
                "-", ""] or not is_english_text_strict(transition_activities_description_translation):
                issues.append({
                    "KEY": key, "Tool": "Tool 1", "QA_By": qa_by,
                    "Question_Label": "transition_activities_description_Translation",
                    "Issue": "If transition_activities_description has value, transition_activities_description_Translation must not be blank, '-' or non-English.",
                    "Choice": transition_activities_description_translation
                })

        final_comments = str(row.get("Final_comments", "")).strip()
        final_comments_translation = str(row.get("Final_comments_Translation", "")).strip()

        if final_comments:
            if not final_comments_translation or final_comments_translation in ["-", ""] or not is_english_text_strict(
                    final_comments_translation):
                issues.append({
                    "KEY": key, "Tool": "Tool 1", "QA_By": qa_by,
                    "Question_Label": "Final_comments_Translation",
                    "Issue": "If Final_comments has value, Final_comments_Translation must not be blank, '-' or non-English.",
                    "Choice": final_comments_translation
                })

        elif not final_comments and final_comments_translation not in ["", "-"]:
            issues.append({
                "KEY": key, "Tool": "Tool 1", "QA_By": qa_by,
                "Question_Label": "Final_comments_Translation",
                "Issue": "If Final_comments is blank, Final_comments_Translation must be blank or '-' only.",
                "Choice": final_comments_translation
            })

        # ==== Helpers: اگر هنوز در بالای فایل نیستند، آنها را اضافه کنید ====
        import re

        _PERSO_ARABIC_RE = re.compile(r'[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF]')


        def is_english_text_strict(text):
            """True اگر متن حروف فارسی/پشتو/عربی نداشته باشد. (اعداد و علامت مجازند)."""
            if text is None:
                return False
            s = str(text).strip()
            if s == "":
                return False
            return _PERSO_ARABIC_RE.search(s) is None


        # ==== شروع بلوک: safe access to other_adult_repeat ====
        # (داخل حلقه برای هر row اجرا شود)

        # 1) اطمینان از وجود DataFrame other_adult_repeat
        if 'other_adult_repeat' in globals():
            other_df = "other_adult_repeat"
        elif 'other_adult_repeat' in locals():
            other_df = "other_adult_repeat"
        else:
            # اگر شیت را قبلاً نخوانده‌اید، یک DataFrame خالی بساز تا خطا ندهد
            other_df = pd.DataFrame(
                columns=["PARENT_KEY", "other_adult_name", "other_adult_role", "other_adult_role_other"])

        # 2) مطمئن شو ستون PARENT_KEY وجود دارد (در غیر این صورت آن را اضافه کن با مقدار خالی)
        if "PARENT_KEY" not in other_df.columns:
            other_df["PARENT_KEY"] = ""

        # 3) فیلتر امن بر اساس key (cast به str و strip تا مقایسه درست باشد)
        parent_key_matches = other_df[other_df["PARENT_KEY"].astype(str).str.strip() == str(key).strip()]

        # حالا validation ها (سه شرط یکجا)

        # مقدارهای محلی از row
        other_adult_repeat_count = str(row.get("other_adult_repeat_count", "")).strip()
        other_adults_present = str(row.get("other_adults_present", "")).strip()

        # 🔹 شرط 1: شمار تکرارها باید برابر با ردیف‌های other_adult_repeat باشد
        if other_adult_repeat_count.isdigit():
            expected_count = int(other_adult_repeat_count)
            actual_count = len(parent_key_matches)
            if expected_count != actual_count:
                issues.append({
                    "KEY": key, "Tool": "Tool 1", "QA_By": qa_by,
                    "Question_Label": "other_adult_repeat_count",
                    "Issue": f"Expected {expected_count} records in other_adult_repeat (PARENT_KEY=={key}) but found {actual_count}.",
                    "Choice": other_adult_repeat_count
                })

        # 🔹 شرط 2: اگر other_adults_present = 1 --> نام‌ها باید موجود و انگلیسی باشند
        if other_adults_present == "1":
            # اگر هیچ ردیفی وجود ندارد، ثبتِ ایراد هم باید انجام شود (نام وجود ندارد)
            if parent_key_matches.empty:
                issues.append({
                    "KEY": key, "Tool": "Tool 1", "QA_By": qa_by,
                    "Question_Label": "other_adult_name",
                    "Issue": "other_adults_present=1 but no records found in other_adult_repeat for this KEY.",
                    "Choice": ""
                })
            else:
                for _, r in parent_key_matches.iterrows():
                    adult_name = str(r.get("other_adult_name", "")).strip()
                    if not adult_name or not is_english_text_strict(adult_name):
                        issues.append({
                            "KEY": key, "Tool": "Tool 1", "QA_By": qa_by,
                            "Question_Label": "other_adult_name",
                            "Issue": "If other_adults_present=1, other_adult_name must not be blank and must be in English (no Dari/Pashto letters).",
                            "Choice": adult_name
                        })

        # 🔹 شرط 3: اگر other_adult_role == 8888 --> other_adult_role_other باید موجود و انگلیسی باشد
        for _, r in parent_key_matches.iterrows():
            role = str(r.get("other_adult_role", "")).strip()
            role_other = str(r.get("other_adult_role_other", "")).strip()
            if role == "8888":
                if not role_other or not is_english_text_strict(role_other):
                    issues.append({
                        "KEY": key, "Tool": "Tool 1", "QA_By": qa_by,
                        "Question_Label": "other_adult_role_other",
                        "Issue": "If other_adult_role=8888, other_adult_role_other must not be blank and must be in English (no Dari/Pashto letters).",
                        "Choice": role_other
                    })
        # ==== پایان بلوک ====

        # --- شرط 1: attendance_sheet_available ---
        attendance_sheet_available = str(row.get("attendance_sheet_available", "")).strip()
        attendance_sheet_photo = str(row.get("attendance_sheet_photo", "")).strip()

        if attendance_sheet_available == "1" and not attendance_sheet_photo:
            issues.append({
                "KEY": key, "Tool": "Tool 1", "QA_By": qa_by,
                "Question_Label": "attendance_sheet_photo",
                "Issue": "If attendance_sheet_available=1, attendance_sheet_photo must not be blank.",
                "Choice": attendance_sheet_photo
            })

        # --- شرط 2: attendance_sheet_photo_QA ---
        attendance_sheet_photo_QA = str(row.get("attendance_sheet_photo_QA", "")).strip()
        allowed_values = ["Blur/Not Visible Photo", "Relevant Photo", "Irrelevant Photo"]

        if attendance_sheet_photo:  # یعنی عکسی وجود دارد
            if not attendance_sheet_photo_QA or attendance_sheet_photo_QA == "-" or attendance_sheet_photo_QA not in allowed_values:
                issues.append({
                    "KEY": key, "Tool": "Tool 1", "QA_By": qa_by,
                    "Question_Label": "attendance_sheet_photo_QA",
                    "Issue": "If attendance_sheet_photo exists, attendance_sheet_photo_QA must not be blank, '-' or outside the allowed values.",
                    "Choice": attendance_sheet_photo_QA
                })

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
                file_name=f"Tool1_Issues_{selected_user}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        else:
            st.success("✅ No issues found for your assigned keys.")