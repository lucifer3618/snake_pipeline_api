import streamlit as st

# Create a function to initialize the session state with needed variables.
# This will only recreate the variables if they don't already exist in the session state.
def initialize_state() -> None:
    for key in ("pipeline_result", "uploaded_digest", "pipeline_status"):
        if key not in st.session_state:
            st.session_state[key] = None
