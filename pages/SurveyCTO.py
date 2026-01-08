import streamlit as st
from PIL import Image
import base64
from io import BytesIO
from pathlib import Path
from theme.theme import apply_theme
apply_theme()

st.set_page_config(page_title="SurveyCTO Access", layout="wide")

THIS_FILE = Path(__file__).resolve()

candidates = [
    THIS_FILE.parents[0],
    THIS_FILE.parents[1],
    THIS_FILE.parents[2],
    THIS_FILE.parents[3],
]

base_dir = None
for p in candidates:
    if (p / "theme" / "assets").exists():
        base_dir = p
        break

if base_dir is None:
    st.error("theme/assets folder not found in expected locations.")
    st.write("Current file:", str(THIS_FILE))
    for i, p in enumerate(candidates):
        st.write(f"Candidate {i}:", str(p))
        st.write("Exists:", (p / "theme" / "assets").exists())
    st.stop()

header_path = base_dir /"theme"/"assets"/"logo"/"surveycto_cover.jpg"
cover_path = base_dir /"theme"/"assets"/"logo"/"generic-post-image.jpg"

if not header_path.exists():
    st.error(f"Header image not found: {header_path}")
    st.write("Assets files:", [x.name for x in (base_dir / "theme" / "assets").glob("*")])
    st.stop()

if not cover_path.exists():
    st.error(f"Cover image not found: {cover_path}")
    st.write("Assets files:", [x.name for x in (base_dir / "theme" / "assets").glob("*")])
    st.stop()

header_img = Image.open(header_path)
st.image(header_img, use_container_width=True)

st.markdown("<hr>", unsafe_allow_html=True)

col1, col2 = st.columns([1, 4])
with col2:
    st.markdown(
        "<h2 style='margin-top:30px;'>Select one of the tabs below to work on your data</h2>",
        unsafe_allow_html=True
    )

st.markdown("---")

tabs = {
    "Design": "https://act4performance.surveycto.com/main.html#Design",
    "Collect": "https://act4performance.surveycto.com/main.html#Collect",
    "Monitor": "https://act4performance.surveycto.com/main.html#Monitor",
    "Export": "https://act4performance.surveycto.com/main.html#Export"
}

cols = st.columns(len(tabs))
for i, (name, url) in enumerate(tabs.items()):
    with cols[i]:
        st.markdown(
            f"""
            <a href="{url}" target="_blank">
                <button style="
                    width:100%;
                    background-color:#4CAF50;
                    color:white;
                    padding:12px 20px;
                    border:none;
                    border-radius:8px;
                    cursor:pointer;
                    font-size:16px;
                ">{name}</button>
            </a>
            """,
            unsafe_allow_html=True
        )

st.markdown("---")

cover_img = Image.open(cover_path)
buffer = BytesIO()
cover_img.save(buffer, format="JPEG")
img_str = base64.b64encode(buffer.getvalue()).decode()

st.markdown(
    f"""
    <div style="
        background-image: url('data:image/jpeg;base64,{img_str}');
        background-size: cover;
        background-position: center;
        width: 100%;
        height: 400px;
        display: flex;
        align-items: center;
        justify-content: center;
        position: relative;
    ">
        <div style="
            background-color: rgba(0,0,0,0.4);
            width: 100%;
            height: 100%;
            position: absolute;
            top: 0;
            left: 0;
        "></div>
        <h2 style="
            color: white;
            z-index: 1;
            text-align: center;
            font-size: 40px;
        ">SurveyCTO Data Management Portal</h2>
    </div>
    """,
    unsafe_allow_html=True
)
