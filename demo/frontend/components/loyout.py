import streamlit as st
import os

# Component used to render the header section
def render_header() -> None:
    st.title("🐍 SnakeVision Lab")
    st.caption(
        "Detector-guided snake identification research dashboard · "
        "Eight Sri Lankan species · Research prototype"
    )


def _get_secrets(name: str, default: str = "") -> str:
    # First check the operating system env for the variable
    if os.getenv(name) is not None:
        return os.environ[name]
    try:
        # if not it looks into stramlit internal secrets (secrets.toml)
        return str(st.secrets.get(name, default))
    except (FileNotFoundError, KeyError):
        return default

# Render side bar and pass the api_key and url
def render_conn_settings_bar() -> tuple[str, str]:
    with st.sidebar:
        st.subheader("Connection settings")
        st.caption("Credentials remain in this Streamlit session and are sent only to the configured API.")
        api_url = st.text_input(
            "API base URL",
            value=_get_secrets("SNAKE_API_URL", "http://127.0.0.1:8080/api/v1"),
        )
        api_key = st.text_input(
            "API key", value=_get_secrets("SNAKE_API_KEY", ""), type="password"
        )
    return api_url, api_key