import streamlit as st

def apply_theme():
    """اعمال تم سفارسی به اپلیکیشن Streamlit"""
    
    # استایل‌های CSS
    css = """
    <style>
    :root {
        /* پالت رنگ سازمانی */
        --unicef-blue: #0077b6;
        --unicef-light-blue: #00b4d8;
        --unicef-dark-blue: #00509e;
        --ppc-orange: #ff6b35;
        --ppc-light-orange: #ff9e6d;
        --success: #2ecc71;
        --warning: #f39c12;
        --info: #3498db;
        
        /* گرادیانت‌ها */
        --bg-gradient: linear-gradient(135deg, #f5f7fa 0%, #e3e9ff 100%);
        --card-gradient: linear-gradient(135deg, #ffffff 0%, #f8faff 100%);
        --header-gradient: linear-gradient(135deg, var(--unicef-blue) 0%, var(--unicef-light-blue) 100%);
        
        /* سایه‌ها */
        --shadow-light: 0 10px 30px rgba(0, 119, 182, 0.08);
        --shadow-medium: 0 15px 40px rgba(0, 119, 182, 0.12);
        --shadow-strong: 0 20px 50px rgba(0, 119, 182, 0.15);
        
        /* انیمیشن‌ها */
        --transition-smooth: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
        --transition-bounce: all 0.6s cubic-bezier(0.68, -0.55, 0.265, 1.55);
        
        /* شکل‌ها */
        --radius-large: 24px;
        --radius-medium: 16px;
        --radius-small: 10px;
    }
    
    [data-theme="dark"] {
        --bg-gradient: linear-gradient(135deg, #0c1a2d 0%, #1a365d 100%);
        --card-gradient: linear-gradient(135deg, #1e293b 0%, #2d3748 100%);
        --shadow-light: 0 10px 30px rgba(0, 0, 0, 0.2);
        --shadow-medium: 0 15px 40px rgba(0, 0, 0, 0.25);
        --shadow-strong: 0 20px 50px rgba(0, 0, 0, 0.3);
    }
    
    /* استایل‌های پایه */
    .stApp {
        background: var(--bg-gradient) !important;
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
    }
    
    /* هدر اصلی */
    .main-header {
        text-align: center;
        padding: 3rem 1rem;
    }
    
    .main-title {
        font-size: 3.5rem !important;
        font-weight: 800 !important;
        background: linear-gradient(135deg, var(--unicef-blue) 0%, var(--unicef-light-blue) 50%, var(--ppc-orange) 100%) !important;
        -webkit-background-clip: text !important;
        background-clip: text !important;
        color: transparent !important;
        margin-bottom: 1rem !important;
    }
    
    /* کارت‌ها */
    .custom-card {
        background: var(--card-gradient);
        border-radius: var(--radius-large);
        padding: 2rem;
        margin: 1.5rem 0;
        box-shadow: var(--shadow-medium);
        border: 1px solid rgba(255, 255, 255, 0.8);
        transition: var(--transition-smooth);
    }
    
    .custom-card:hover {
        transform: translateY(-5px);
        box-shadow: var(--shadow-strong);
    }
    
    /* دکمه‌ها */
    .custom-button {
        background: linear-gradient(135deg, var(--unicef-blue) 0%, var(--ppc-orange) 100%) !important;
        color: white !important;
        border: none !important;
        border-radius: var(--radius-medium) !important;
        padding: 0.75rem 2rem !important;
        font-weight: 600 !important;
        transition: var(--transition-bounce) !important;
    }
    
    .custom-button:hover {
        transform: translateY(-3px) scale(1.05) !important;
        box-shadow: 0 10px 25px rgba(0, 119, 182, 0.3) !important;
    }
    </style>
    """
    
    # لینک فونت Inter
    fonts = """
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
    """
    
    # اعمال استایل‌ها
    st.markdown(fonts + css, unsafe_allow_html=True)
