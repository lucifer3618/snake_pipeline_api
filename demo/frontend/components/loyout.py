import streamlit as st

def render_header() -> None:
    st.title("🐍 SnakeVision Lab")
    st.caption(
        "Detector-guided snake identification research dashboard · "
        "Eight Sri Lankan species · Research prototype"
    )