import io
from PIL import Image, ImageOps

# This function takes in image bytes, opens the image using PIL, applies EXIF orientation correction, and converts 
# it to RGB format. It returns the processed PIL Image object.
# This use the same convention as pipeline
def uploaded_image(image_bytes: bytes) -> Image.Image:
    return ImageOps.exif_transpose(Image.open(io.BytesIO(image_bytes))).convert("RGB")
