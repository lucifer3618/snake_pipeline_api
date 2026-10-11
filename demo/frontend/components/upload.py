from __future__ import annotations

import hashlib
from dataclasses import dataclass

import streamlit as st
from PIL import Image

from utils.standerdize import uploaded_image

# Immutable dataclass for image upload output
@dataclass(frozen=True)
class UploadSelection:
    file_name: str | None
    media_type: str
    image_bytes: bytes | None
    image: Image.Image | None
    include_mask: bool
    include_roi: bool
    include_gradcam: bool
    run: bool


def render_upload_panel() -> UploadSelection:
    with st.container(border=True):
        st.info(
            "Supported scope: this closed-set prototype distinguishes eight supported Sri Lankan snake "
            "species. It does not independently prove that an arbitrary upload contains a snake."
        )

        # Allow users to upload an image and saves as a PIL object
        upload = st.file_uploader(
            "Upload a snake image", type=["jpg", "jpeg", "png", "webp", "bmp"],
            help="Maximum backend upload size: 10 MB."
        )

        # INtialize variables to hold the image bytes and the PIL Image object
        image_bytes: bytes | None = None
        image: Image.Image | None = None

        if upload is not None:
            # Set the uploaded image bytes and compute its SHA-256 digest to check for changes
            image_bytes = upload.getvalue()
            digest = hashlib.sha256(image_bytes).hexdigest()
            if digest != st.session_state.uploaded_digest:
                st.session_state.uploaded_digest = digest
                st.session_state.pipeline_result = None
            try:
                image = uploaded_image(image_bytes)
            except Exception as error:
                st.error(f"The selected file could not be decoded: {error}")

        # Render these components only if an image has been uploaded, otherwise default to True for all options
        if upload is not None:
            options = st.columns([2.2, 1, 1, 1])
            options[0].markdown(
                f"**{upload.name}**  \n{image.width if image else '—'} x "
                f"{image.height if image else '—'} pixels · {len(image_bytes or b'') / 1024:.1f} KB"
            )
            include_mask = options[1].checkbox("Mask overlay", value=True)
            include_roi = options[2].checkbox("ROI output", value=True)
            include_gradcam = options[3].checkbox("Grad-CAM", value=True)
        else:
            include_mask = include_roi = include_gradcam = True

        confirmed = st.checkbox(
            "I confirm that the uploaded image is intended to contain a visible snake.",
            help="This defines the supported input scope; it is not automated snake-presence verification.",
        )
        run = st.button(
            "Run detector-guided pipeline", type="primary", width="stretch",
            disabled=image_bytes is None or image is None or not confirmed,
        )
        if image_bytes is not None and not confirmed:
            st.caption("Confirm the supported input scope to enable inference.")

    # Return an instance of UploadSelection with the current state of the upload panel
    return UploadSelection(
        file_name=upload.name if upload is not None else None,
        media_type=(upload.type or "application/octet-stream") if upload is not None else "application/octet-stream",
        image_bytes=image_bytes, 
        image=image, 
        include_mask=include_mask,
        include_roi=include_roi, 
        include_gradcam=include_gradcam, 
        run=run,
    )
