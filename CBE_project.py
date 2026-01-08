import streamlit as st
from PIL import Image
from pathlib import Path
from theme.theme import apply_theme
apply_theme()


st.set_page_config(page_title="Welcome | CBE Dashboard", layout="wide")

THIS_FILE = Path(__file__).resolve()
candidates = [THIS_FILE.parents[0], THIS_FILE.parents[1], THIS_FILE.parents[2], THIS_FILE.parents[3]]

base_dir = None
for p in candidates:
    if (p / "theme" / "assets").exists():
        base_dir = p
        break

if base_dir is None:
    st.error("theme/assets folder not found.")
    st.write("Current file:", str(THIS_FILE))
    st.stop()

unicef_logo_path = base_dir / "theme"/"assets"/"logo"/"unicef.png"
ppc_logo_path = base_dir / "theme"/"assets"/"logo"/"ppc.png"

if not unicef_logo_path.exists():
    st.error(f"UNICEF logo not found: {unicef_logo_path}")
    st.stop()

if not ppc_logo_path.exists():
    st.error(f"PPC logo not found: {ppc_logo_path}")
    st.stop()

col1, col2, col3 = st.columns([1, 3, 1])
with col1:
    st.image(Image.open(unicef_logo_path), width=110)
with col2:
    st.image(Image.open(ppc_logo_path), width=140)

st.markdown(
    "<h1 style='text-align:center; color:#0077b6;'>Welcome to CBE Monitoring Dashboard</h1>",
    unsafe_allow_html=True
)

st.markdown(
    """
    This dashboard has been developed for **UNICEF’s Community-Based Education (CBE)** project.  
    **PPC**, as the **Third Party Monitoring (TPM)** partner, is responsible for collecting, validating, and reporting monitoring data from the field.
    """
)

st.subheader("Project Objectives")
st.markdown(
    """
    - Improve access to education in remote areas  
    - Ensure quality learning environment for CBE classes  
    - Monitor teacher performance and student attendance  
    - Provide transparent data for decision-making  
    """
)

st.subheader("Dashboard Features")
cols = st.columns(3)
with cols[0]:
    st.info("Upload and validate survey data")
with cols[1]:
    st.success("Track monitoring results (QC_Log)")
with cols[2]:
    st.warning("Export reports for analysis")
