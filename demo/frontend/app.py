import streamlit as st

from components.loyout import render_header, render_conn_settings_bar, render_connection_status
from api.client import SnakeApiClient
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

# Create an instance of the SnakeApiClient with the provided API URL and API key.
client = SnakeApiClient(base_url=api_url, api_key=api_key)

# Render the connection status of the API and display relevant information on the side bar.
render_connection_status(client)