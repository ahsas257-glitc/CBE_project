import streamlit as st
from PIL import Image
from pathlib import Path
import base64

# اضافه کردن theme به path
import sys
sys.path.append(str(Path(__file__).parent))

# اعمال تم
from theme.theme import apply_theme
apply_theme()

# تنظیمات صفحه
st.set_page_config(
    page_title="Welcome | CBE Dashboard",
    page_icon="🏫",
    layout="wide",
    initial_sidebar_state="expanded"
)

# پیدا کردن مسیر فایل‌ها
THIS_FILE = Path(__file__).resolve()
BASE_DIR = THIS_FILE.parent

# مسیر لوگوها
LOGO_DIR = BASE_DIR / "theme" / "assets" / "logo"
UNICEF_LOGO = LOGO_DIR / "unicef.png"
PPC_LOGO = LOGO_DIR / "ppc.png"

# تابع برای تبدیل عکس به base64
def image_to_base64(image_path):
    with open(image_path, "rb") as img_file:
        return base64.b64encode(img_file.read()).decode()

# تبدیل لوگوها
unicef_base64 = image_to_base64(UNICEF_LOGO) if UNICEF_LOGO.exists() else ""
ppc_base64 = image_to_base64(PPC_LOGO) if PPC_LOGO.exists() else ""

# HTML برای صفحه اصلی
main_html = f"""
<div style="max-width: 1400px; margin: 0 auto; padding: 2rem;">

    <!-- هدر لوگوها -->
    <div style="
        background: linear-gradient(135deg, #ffffff 0%, #f8faff 100%);
        backdrop-filter: blur(20px);
        border-radius: 24px;
        padding: 2.5rem;
        margin: 2rem auto 3rem;
        box-shadow: 0 15px 40px rgba(0, 119, 182, 0.12);
        border: 1px solid rgba(255, 255, 255, 0.8);
        text-align: center;
        position: relative;
    ">
        <div style="display: flex; justify-content: center; align-items: center; gap: 4rem; flex-wrap: wrap;">
            <div style="text-align: center;">
                <img src="data:image/png;base64,{unicef_base64}" 
                     alt="UNICEF Logo" 
                     style="width: 140px; height: auto; transition: transform 0.3s ease;">
            </div>
            <div style="text-align: center;">
                <img src="data:image/png;base64,{ppc_base64}" 
                     alt="PPC Logo" 
                     style="width: 160px; height: auto; transition: transform 0.3s ease;">
            </div>
        </div>
    </div>

    <!-- عنوان اصلی -->
    <div style="text-align: center; margin: 3rem 0;">
        <h1 class="main-title">Welcome to CBE Monitoring Dashboard</h1>
        <p style="font-size: 1.4rem; color: #666; max-width: 800px; margin: 1rem auto; line-height: 1.6;">
            This dashboard has been developed for <strong>UNICEF's Community-Based Education (CBE)</strong> project.  
            <strong>PPC</strong>, as the <strong>Third Party Monitoring (TPM)</strong> partner, is responsible for 
            collecting, validating, and reporting monitoring data from the field.
        </p>
    </div>

    <!-- اهداف پروژه -->
    <div class="custom-card">
        <h2 style="color: var(--unicef-blue); margin-bottom: 2rem; font-size: 2rem;">
            🎯 Project Objectives
        </h2>
        
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 1.5rem;">
            <div style="
                background: rgba(0, 119, 182, 0.05);
                padding: 1.5rem;
                border-radius: 16px;
                border-left: 4px solid var(--unicef-blue);
            ">
                <h4 style="color: #333; margin-bottom: 0.5rem;">🏫 Improve Access to Education</h4>
                <p style="color: #666; line-height: 1.6;">
                    Expand quality education reach to remote and underserved communities through sustainable CBE programs.
                </p>
            </div>
            
            <div style="
                background: rgba(0, 119, 182, 0.05);
                padding: 1.5rem;
                border-radius: 16px;
                border-left: 4px solid var(--ppc-orange);
            ">
                <h4 style="color: #333; margin-bottom: 0.5rem;">📊 Quality Learning Environment</h4>
                <p style="color: #666; line-height: 1.6;">
                    Monitor and ensure optimal classroom conditions, teaching resources, and learning atmosphere.
                </p>
            </div>
            
            <div style="
                background: rgba(0, 119, 182, 0.05);
                padding: 1.5rem;
                border-radius: 16px;
                border-left: 4px solid var(--success);
            ">
                <h4 style="color: #333; margin-bottom: 0.5rem;">👨‍🏫 Performance Monitoring</h4>
                <p style="color: #666; line-height: 1.6;">
                    Track teacher performance and student attendance across all CBE centers systematically.
                </p>
            </div>
        </div>
    </div>

    <!-- قابلیت‌های داشبورد -->
    <div class="custom-card">
        <h2 style="color: var(--unicef-blue); margin-bottom: 2rem; font-size: 2rem;">
            ✨ Dashboard Features
        </h2>
        
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 2rem;">
            <div style="
                background: white;
                padding: 2rem;
                border-radius: 20px;
                text-align: center;
                box-shadow: 0 8px 25px rgba(0, 0, 0, 0.05);
                border-top: 4px solid var(--info);
                transition: all 0.3s ease;
            ">
                <div style="
                    width: 70px;
                    height: 70px;
                    background: linear-gradient(135deg, var(--info), #2980b9);
                    border-radius: 50%;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    margin: 0 auto 1.5rem;
                    color: white;
                    font-size: 1.8rem;
                ">
                    📤
                </div>
                <h3 style="color: #333; margin-bottom: 1rem;">Data Management</h3>
                <p style="color: #666; line-height: 1.6;">
                    Upload and validate survey data with automated quality checks.
                </p>
            </div>
            
            <div style="
                background: white;
                padding: 2rem;
                border-radius: 20px;
                text-align: center;
                box-shadow: 0 8px 25px rgba(0, 0, 0, 0.05);
                border-top: 4px solid var(--success);
                transition: all 0.3s ease;
            ">
                <div style="
                    width: 70px;
                    height: 70px;
                    background: linear-gradient(135deg, var(--success), #27ae60);
                    border-radius: 50%;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    margin: 0 auto 1.5rem;
                    color: white;
                    font-size: 1.8rem;
                ">
                    📈
                </div>
                <h3 style="color: #333; margin-bottom: 1rem;">Real-time Monitoring</h3>
                <p style="color: #666; line-height: 1.6;">
                    Track monitoring results through QC_Log with interactive visualizations.
                </p>
            </div>
            
            <div style="
                background: white;
                padding: 2rem;
                border-radius: 20px;
                text-align: center;
                box-shadow: 0 8px 25px rgba(0, 0, 0, 0.05);
                border-top: 4px solid var(--warning);
                transition: all 0.3s ease;
            ">
                <div style="
                    width: 70px;
                    height: 70px;
                    background: linear-gradient(135deg, var(--warning), #e67e22);
                    border-radius: 50%;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    margin: 0 auto 1.5rem;
                    color: white;
                    font-size: 1.8rem;
                ">
                    📋
                </div>
                <h3 style="color: #333; margin-bottom: 1rem;">Advanced Analytics</h3>
                <p style="color: #666; line-height: 1.6;">
                    Generate comprehensive reports and export data for in-depth analysis.
                </p>
            </div>
        </div>
    </div>

</div>
"""

# نمایش HTML
st.markdown(main_html, unsafe_allow_html=True)

# سایدبار
with st.sidebar:
    st.markdown("### 🎨 Theme Settings")
    theme = st.selectbox(
        "Select Theme",
        ["Light", "Dark"],
        index=0
    )
    
    st.markdown("---")
    
    st.markdown("### 🔗 Quick Links")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("📊 Dashboard", use_container_width=True):
            st.switch_page("pages/dashboard.py")
    
    with col2:
        if st.button("📤 Upload", use_container_width=True):
            st.switch_page("pages/upload.py")
    
    if st.button("📋 Generate Report", use_container_width=True):
        st.switch_page("pages/reports.py")
    
    st.markdown("---")
    
    st.markdown("### 🏛️ Partners")
    col_logo1, col_logo2 = st.columns(2)
    with col_logo1:
        st.image(Image.open(UNICEF_LOGO), width=80)
    with col_logo2:
        st.image(Image.open(PPC_LOGO), width=100)

# فوت‌نوت
st.markdown("---")
st.markdown(
    """
    <div style="text-align: center; color: #666; padding: 2rem 0; font-size: 0.9rem;">
        © 2024 UNICEF CBE Monitoring Dashboard | Powered by PPC - Third Party Monitoring Partner<br>
        <small>This platform is designed for monitoring and evaluation purposes only.</small>
    </div>
    """,
    unsafe_allow_html=True
)
