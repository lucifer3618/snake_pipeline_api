import streamlit as st

from components.loyout import render_header
from utils.state import initialize_state



# Set the page configuration for the Streamlit app.
st.set_page_config(
    page_title="SnakeVision Lab",
    page_icon="🐍",
    layout="wide",
    initial_sidebar_state="collapsed",
    menu_items={"About": "Detector-guided Sri Lankan snake identification research dashboard."},
)

# Initialize the session state with needed variables.
initialize_state()

# Render the header of the app.
render_header()