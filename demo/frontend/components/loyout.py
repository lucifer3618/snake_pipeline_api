import streamlit as st
import os

from api.client import SnakeApiClient, ApiError

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
        api_key = _get_secrets("SNAKE_API_KEY", "")
    return api_url, api_key

# Render the connection status of the API and display relevant information on the side bar
def render_connection_status(client: SnakeApiClient) -> None:
    with st.sidebar:
        st.divider()
        if st.button("Check model status", width="stretch"):
            try:
                # Take the status of the pipeline and store it in the session state for later use
                st.session_state.pipeline_status = client.pipeline_status()
                st.success("Pipeline service reached successfully")
            except ApiError as error:
                st.error(str(error))
        status = st.session_state.get("pipeline_status")
        if status:
            with st.container(horizontal=True, vertical_alignment="center", horizontal_alignment="center"):
                st.markdown(f"**{'Ready' if status.get('ready') else 'Unavailable'}**")
                st.write("🟢" if status.get("ready") else "🔴")
            st.table(
                {
                    "Metric": [
                        "Detector count",
                        "Classifier count",
                        "Device",
                    ],
                    "Value": [
                        str(status.get("detector_count", 0)),
                        str(status.get("classifier_count", 0)),
                        str(status.get("device", "unknown")),
                    ],
                }
            )
        st.divider()
        st.caption("Research demonstration only. It is not medical advice or emergency assessment.")
        st.markdown(
            """
            <a href="/.auth/logout" target="_self" style="
                display: block;
                width: 100%;
                padding: 0.5rem 0.75rem;
                border: 1px solid rgba(128, 128, 128, 0.4);
                border-radius: 0.5rem;
                color: inherit;
                text-align: center;
                text-decoration: none;
            ">Log out</a>
            """,
            unsafe_allow_html=True,
        )

# Footer section
def render_footer() -> None:
    st.divider()
    st.caption(
        "Research demonstration only. Do not use the output to delay emergency treatment, "
        "handle a snake, or replace qualified identification."
    )
