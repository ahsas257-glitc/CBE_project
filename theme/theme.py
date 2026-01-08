import streamlit as st
from pathlib import Path

def apply_theme():
    base_dir = Path(__file__).resolve().parents[1]
    css_path = base_dir / "theme" / "style.css"
    css = css_path.read_text(encoding="utf-8")
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)

def asset_path(filename: str) -> str:
    base_dir = Path(__file__).resolve().parents[1]
    return str(base_dir / "theme" / "assets" / filename)
