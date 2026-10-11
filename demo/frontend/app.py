import streamlit as st

from components.loyout import render_header, render_conn_settings_bar
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

# Render connection settings bar and extract api_key and api_url which are forwarded
api_url, api_key = render_conn_settings_bar()