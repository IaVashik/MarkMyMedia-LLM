import os

from .utils import _wrap_text

from .errors import ImageMarkingError, InputFileNotFoundError
from PIL import Image, ImageDraw, ImageFont

def mark_image(
    input_path: str,
    output_path: str = None,
    overlay_text: str = None,
) -> None:
    """
    Overlay file name text on an image.

    The text is centered with a proportional font size relative to the image height,
    ensuring a consistent look across different resolutions. A semi-transparent
    background is drawn behind the text for readability.

    Args:
        input_path (str): Path to the input image file.
        output_path (str, optional): Output path. Defaults to a modified name
                                     (e.g., 'image.jpg' -> 'image_marked.jpg').
    Raises:
        ImageMarkingError: On any processing failure.
    """
    if not os.path.exists(input_path):
        raise ImageMarkingError(f"File not found: {input_path}")

    if output_path is None:
        base, ext = os.path.splitext(input_path)
        output_path = f"{base}_marked{ext}"

    try:
        img = Image.open(input_path)
        
        # Convert to RGBA for drawing with transparency, create draw object
        draw = ImageDraw.Draw(img, "RGB")
        width, height = img.size
        
        # Calculate a font size proportional to the image height
        font_size = max(10, int(height / 30))
        
        try:
            # Attempt to load a common, high-quality font
            font = ImageFont.truetype("DejaVuSans.ttf", size=font_size)
        except IOError:
            # Fallback to Pillow's default font if not found
            font = ImageFont.load_default()
        
        if overlay_text is None:
            overlay_text = "Filename: " + os.path.basename(input_path) 
        
        avg_char_width = font.getlength("abcdefghijklmnopqrstuvwxyz") / 26
        margin = int(width * 0.05)
        max_chars = int((width - 2 * margin) / avg_char_width)
        wrapped_text = _wrap_text(overlay_text, max_chars)

        # Position for the text block
        margin = int(font_size * 0.4)
        text_pos = (margin, margin)
        
        draw.text(
            text_pos, 
            wrapped_text, 
            font=font, 
            fill="white", 
            stroke_width=3,
            stroke_fill="black"
        )

        img.save(output_path)

    except FileNotFoundError:
        raise InputFileNotFoundError(input_path)
    except Exception as e:
        raise ImageMarkingError(f"An unexpected error occurred: {e}") from e
