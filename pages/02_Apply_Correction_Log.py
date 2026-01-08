import streamlit as st
import pandas as pd
from io import BytesIO
import gspread
from google.oauth2.service_account import Credentials

st.set_page_config(page_title="CBE Correction Log", layout="wide")
st.title("Apply Correction Log to Uploaded File")

SPREADSHEET_KEY = "1lkztBZ4eG1BQx-52XgnA6w8YIiw-Sm85pTlQQziurfw"
CORRECTION_SHEET = "Correction_Log"

def load_corrections():
    scopes = ["https://www.googleapis.com/auth/spreadsheets.readonly"]
    creds = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=scopes
    )
    client = gspread.authorize(creds)
    ws = client.open_by_key(SPREADSHEET_KEY).worksheet(CORRECTION_SHEET)
    df = pd.DataFrame(ws.get_all_records())
    df.columns = [c.strip() for c in df.columns]
    required = {"Tool_Name", "Sheet_name", "KEY", "Question", "new_value"}
    if not required.issubset(df.columns):
        raise ValueError("Invalid Correction_Log structure")
    return df

uploaded_file = st.file_uploader("Upload Excel file", type=["xlsx"])

if not uploaded_file:
    st.stop()

try:
    all_sheets = pd.read_excel(uploaded_file, sheet_name=None, dtype=str)
except Exception as e:
    st.error(str(e))
    st.stop()

try:
    df_corrections = load_corrections()
except Exception as e:
    st.error(str(e))
    st.stop()

tool_name = st.selectbox(
    "Select Tool Name",
    sorted(df_corrections["Tool_Name"].dropna().unique().tolist())
)

relevant = df_corrections[df_corrections["Tool_Name"] == tool_name].copy()

if relevant.empty:
    st.warning("No corrections found for selected tool")
    st.stop()

summary = (
    relevant.groupby("Sheet_name")
    .size()
    .reset_index(name="Corrections_Count")
    .sort_values("Corrections_Count", ascending=False)
)

st.metric("Total Corrections", int(len(relevant)))
st.metric("Sheets With Corrections", int(summary.shape[0]))
st.dataframe(summary, use_container_width=True)

with st.expander("Preview Corrections"):
    st.dataframe(
        relevant[["Sheet_name", "KEY", "Question", "new_value"]].head(50),
        use_container_width=True
    )

if not st.button("Apply Corrections"):
    st.stop()

updated_sheets = {}
applied_log = []
total_applied = 0

for sheet_name, df in all_sheets.items():
    df_updated = df.copy()

    sheet_corr = relevant[relevant["Sheet_name"] == sheet_name]
    if sheet_corr.empty or "KEY" not in df_updated.columns:
        updated_sheets[sheet_name] = df_updated
        continue

    df_updated["KEY"] = df_updated["KEY"].astype(str)

    for _, row in sheet_corr.iterrows():
        key = str(row["KEY"])
        col = str(row["Question"]).strip()
        new_val = "" if pd.isna(row["new_value"]) else str(row["new_value"])

        if col in df_updated.columns:
            mask = df_updated["KEY"] == key
            if mask.any():
                old_val = df_updated.loc[mask, col].iloc[0]
                df_updated.loc[mask, col] = new_val
                total_applied += 1
                applied_log.append({
                    "Sheet": sheet_name,
                    "KEY": key,
                    "Column": col,
                    "Old_Value": old_val,
                    "New_Value": new_val
                })

    updated_sheets[sheet_name] = df_updated

st.success(f"Applied {total_applied} corrections")

with st.expander("Applied Changes Log"):
    if applied_log:
        st.dataframe(pd.DataFrame(applied_log), use_container_width=True)

buffer = BytesIO()
with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
    for sh, df_out in updated_sheets.items():
        df_out.to_excel(writer, sheet_name=sh, index=False)

buffer.seek(0)

st.download_button(
    label="Download Corrected File",
    data=buffer,
    file_name=uploaded_file.name.replace(".xlsx", "_Corrected.xlsx"),
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)
