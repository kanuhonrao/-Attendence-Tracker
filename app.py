import pathlib
import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(
    page_title="Attendance & Interactive Calendar Tracker",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
    <style>
    .block-container { padding: 0 !important; max-width: 100% !important; }
    header, footer, [data-testid="stHeader"] { display: none !important; }
    iframe { width: 100% !important; min-height: 100vh !important; border: none !important; }
    </style>
    """,
    unsafe_allow_html=True,
)

html_content = pathlib.Path("index.html").read_text(encoding="utf-8")
components.html(html_content, height=1850, scrolling=True)
