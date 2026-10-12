import streamlit as st

from components.loyout import render_header, render_conn_settings_bar, render_connection_status, render_footer
from components.evidence import render_research_evidence
from components.upload import render_upload_panel
from api.client import SnakeApiClient, ApiError
from components.results import render_pipeline_result
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

# Render the research evidence section of the app, which displays validated quantitative evidence
# from the matched five-fold experiment.
render_research_evidence()

# Render the upload panel, which allows users to upload snake images and configure inference options.
selection = render_upload_panel()

# If user requests to run and if image exsists, then run the inference pipeline and store the result 
# in the session state.
if selection.run and selection.image_bytes is not None and selection.file_name is not None:
    try:
        with st.spinner("Running detector cascade, ROI extraction and five-model ensemble…"):
            st.session_state.pipeline_result = client.predict_pipeline(
                selection.image_bytes,
                selection.file_name,
                selection.media_type,
                include_mask_overlay=selection.include_mask,
                include_roi_crop=selection.include_roi,
                include_gradcam=selection.include_gradcam,
            )
    except ApiError as error:
        st.error(str(error))

if selection.image is not None:
    if st.session_state.pipeline_result:
        render_pipeline_result(selection.image, st.session_state.pipeline_result)
    else:
        with st.container(border=True):
            st.image(selection.image, caption="Ready for inference", width="stretch")

# Render the footer section
render_footer()