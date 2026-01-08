import streamlit as st
from PIL import Image
from pathlib import Path

THIS_FILE = Path(__file__).resolve()
candidates = [THIS_FILE.parents[0], THIS_FILE.parents[1], THIS_FILE.parents[2], THIS_FILE.parents[3]]

base_dir = None
for p in candidates:
    if (p / "theme" / "assets").exists():
        base_dir = p
        break

if base_dir is None:
    st.error("theme/assets folder not found.")
    st.stop()

unicef_logo_path = base_dir / "theme" / "assets" / "logo" / "unicef.png"
ppc_logo_path = base_dir / "theme" / "assets" / "logo" / "ppc.png"

if not unicef_logo_path.exists():
    st.error(f"UNICEF logo not found: {unicef_logo_path}")
    st.stop()

if not ppc_logo_path.exists():
    st.error(f"PPC logo not found: {ppc_logo_path}")
    st.stop()

# استایل‌های سفارشی
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
</style>
""", unsafe_allow_html=True)

# ساختار HTML اصلی
st.markdown("""
<div class="main-container">
    <!-- هدر لوگوها -->
    <div class="logo-header">
        <div class="logo-grid">
            <div class="logo-item">
                <div class="logo-badge">
                    <img src="data:image/png;base64,{}" alt="UNICEF Logo" width="120">
                </div>
            </div>
            <div class="logo-item">
                <div class="logo-badge">
                    <img src="data:image/png;base64,{}" alt="PPC Logo" width="150">
                </div>
            </div>
        </div>
    </div>
    
    <!-- عنوان اصلی -->
    <div class="main-title">
        <h1>Welcome to CBE Monitoring Dashboard</h1>
        <p class="title-subtitle">
            A collaborative platform for UNICEF's Community-Based Education program, 
            powered by PPC as the Third Party Monitoring partner.
        </p>
    </div>
    
    <!-- بخش مقدمه -->
    <div class="content-section">
        <h2 class="section-title">Project Overview</h2>
        <p style="font-size: 1.2rem; line-height: 1.8; color: #555;">
            This advanced monitoring dashboard has been developed to support <strong>UNICEF's Community-Based Education (CBE)</strong> 
            initiative across remote regions. <strong>PPC</strong>, serving as the <strong>Third Party Monitoring (TPM)</strong> 
            partner, ensures rigorous data collection, validation, and comprehensive reporting from field operations.
        </p>
    </div>
    
    <!-- اهداف پروژه -->
    <div class="content-section">
        <h2 class="section-title">Project Objectives</h2>
        <ul class="goals-list">
            <li class="goal-item">
                <div class="goal-icon">🎯</div>
                <div class="goal-content">
                    <h4>Enhanced Educational Access</h4>
                    <p>Expand quality education reach to the most remote and underserved communities through sustainable CBE programs.</p>
                </div>
            </li>
            <li class="goal-item">
                <div class="goal-icon">🏫</div>
                <div class="goal-content">
                    <h4>Quality Learning Environment</h4>
                    <p>Monitor and improve classroom conditions, teaching resources, and overall learning atmosphere for CBE students.</p>
                </div>
            </li>
            <li class="goal-item">
                <div class="goal-icon">📊</div>
                <div class="goal-content">
                    <h4>Performance Tracking</h4>
                    <p>Systematically track teacher performance, student attendance, and learning outcomes across all CBE centers.</p>
                </div>
            </li>
            <li class="goal-item">
                <div class="goal-icon">🔍</div>
                <div class="goal-content">
                    <h4>Data-Driven Decision Making</h4>
                    <p>Provide transparent, real-time data analytics to support evidence-based policy and program decisions.</p>
                </div>
            </li>
        </ul>
    </div>
    
    <!-- قابلیت‌های داشبورد -->
    <div class="content-section">
        <h2 class="section-title">Dashboard Capabilities</h2>
        <div class="features-grid">
            <div class="feature-card">
                <div class="feature-icon">📤</div>
                <h3>Smart Data Management</h3>
                <p>Upload, validate, and process monitoring survey data with automated quality checks and validation rules.</p>
            </div>
            <div class="feature-card">
                <div class="feature-icon">📈</div>
                <h3>Real-Time Monitoring</h3>
                <p>Track field monitoring results through QC_Log with interactive visualizations and performance indicators.</p>
            </div>
            <div class="feature-card">
                <div class="feature-icon">📋</div>
                <h3>Advanced Analytics</h3>
                <p>Generate comprehensive reports, export data for in-depth analysis, and identify trends and patterns.</p>
            </div>
        </div>
    </div>
    
    <!-- دکمه اقدام -->
    <div class="cta-section">
        <h2 style="font-size: 2rem; margin-bottom: 2rem; color: var(--unicef-blue);">
            Ready to Explore the Data?
        </h2>
        <p style="font-size: 1.2rem; margin-bottom: 2.5rem; color: #666;">
            Start exploring monitoring insights, generating reports, and making data-driven decisions.
        </p>
        <button class="cta-button" onclick="location.href='/data_upload'">
            <span>Get Started</span>
            <span>→</span>
        </button>
    </div>
    
    <!-- فوتر -->
    <div class="footer">
        <div class="footer-logos">
            <img src="data:image/png;base64,{}" alt="UNICEF" width="80">
            <img src="data:image/png;base64,{}" alt="PPC" width="100">
        </div>
        <p>© 2024 UNICEF CBE Monitoring Dashboard | Powered by PPC - Third Party Monitoring Partner</p>
        <p style="font-size: 0.8rem; opacity: 0.7; margin-top: 0.5rem;">
            This platform is designed for monitoring and evaluation purposes only.
        </p>
    </div>
</div>
""".format(
    # Base64 encoded logos (در عمل باید از فایل‌های واقعی استفاده شود)
    "UNICEF_BASE64_PLACEHOLDER",
    "PPC_BASE64_PLACEHOLDER",
    "UNICEF_BASE64_PLACEHOLDER_SMALL",
    "PPC_BASE64_PLACEHOLDER_SMALL"
), unsafe_allow_html=True)

# نمایش لوگوها در سایدبار کوچک
with st.sidebar:
    st.markdown("### Partners")
    col1, col2 = st.columns(2)
    with col1:
        st.image(Image.open(unicef_logo_path), width=80)
    with col2:
        st.image(Image.open(ppc_logo_path), width=100)
    
    st.markdown("---")
    st.markdown("### Quick Access")
    if st.button("📊 View Dashboard"):
        st.switch_page("pages/dashboard.py")
    if st.button("📤 Upload Data"):
        st.switch_page("pages/upload.py")
    if st.button("📋 Generate Report"):
        st.switch_page("pages/reports.py")

# لود کردن CSS
def load_css():
    css_path = base_dir / "theme" / "theme.css"
    if css_path.exists():
        with open(css_path) as f:
            st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)
    else:
        st.markdown('<style>' + '''
        /* استایل‌های پیش‌فرض در صورت عدم وجود فایل CSS */
        body { font-family: 'Inter', sans-serif; }
        .stApp { background: linear-gradient(135deg, #f5f7fa 0%, #e3e9ff 100%); }
        ''' + '</style>', unsafe_allow_html=True)

load_css()
