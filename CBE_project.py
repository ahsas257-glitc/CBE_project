import streamlit as st

st.set_page_config(page_title="Welcome | CBE Dashboard", layout="wide")

col1, col2, col3 = st.columns([1,3,1])
with col1:
    st.image(r'C:\Users\LENOVO\CBE_Dashboard\1200px-UNICEF_Logo.png', width=100)
with col2:
    st.image(r'C:\Users\LENOVO\CBE_Dashboard\fInal logo.png', width=100)

st.markdown("<h1 style='text-align: center; color: #0077b6;'>Welcome to CBE Monitoring Dashboard</h1>", unsafe_allow_html=True)

st.markdown("""
This dashboard has been developed for **UNICEF’s Community-Based Education (CBE)** project.  
**PPC**, as the **Third Party Monitoring (TPM)** partner, is responsible for collecting, validating, and reporting monitoring data from the field.
""")

st.subheader("🎯 Project Objectives")
st.markdown("""
- Improve access to education in remote areas  
- Ensure quality learning environment for CBE classes  
- Monitor teacher performance and student attendance  
- Provide transparent data for decision-making
""")

st.subheader("🛠️ Dashboard Features")
cols = st.columns(3)
with cols[0]:
    st.info("📥 Upload and validate survey data")
with cols[1]:
    st.success("📊 Track monitoring results (QC_Log)")
with cols[2]:
    st.warning("📑 Export reports for analysis")

