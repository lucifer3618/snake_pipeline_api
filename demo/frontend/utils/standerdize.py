import io
from PIL import Image, ImageOps
import streamlit as st

# This function takes in image bytes, opens the image using PIL, applies EXIF orientation correction, and converts 
# it to RGB format. It returns the processed PIL Image object.
# This use the same convention as pipeline
def uploaded_image(image_bytes: bytes) -> Image.Image:
    return ImageOps.exif_transpose(Image.open(io.BytesIO(image_bytes))).convert("RGB")


# This function takes in a label string, replaces underscores with spaces, 
# splits the string into parts, capitalizes the first part, and converts the rest to lowercase. 
def display_species(value: str | None) -> str:
    if not value:
        return "Not released"
    parts = value.replace("_", " ").split()
    return " ".join([parts[0].capitalize(), *[part.lower() for part in parts[1:]]])

# This function takes in a float value and an optional number of digits (default is 1).
def percentage(value: float | None, digits: int = 1) -> str:
    return "—" if value is None else f"{value * 100:.{digits}f}%"

# This function use to take a float value and returns a string representation of the value in milliseconds format.
def milliseconds(value: float | None) -> str:
    return "—" if value is None else f"{value:,.1f} ms"

# This function takes in a label string, a value string, and an optional note string. 
# It uses Streamlit's metric component to display the label and value wiht error handling
def card(label: str, value: str, note: str = "") -> None:
    st.metric(label, value)
    if note:
        st.caption(note)