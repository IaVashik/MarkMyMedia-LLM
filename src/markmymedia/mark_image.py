import os
from pathlib import Path

from .utils import _wrap_text
from .errors import (
    ImageMarkingError,
    InputFileNotFoundError,
    MarkerError,
    UnsupportedFileTypeError,
    InvalidOutputPathError,
    FileError,
)
from .formats import IMAGE_EXTS
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
        InputFileNotFoundError: If the input file does not exist.
        UnsupportedFileTypeError: If the input file is not a supported image format.
        InvalidOutputPathError: If the specified output path is invalid.
        ImageMarkingError: On any other processing failure.
    """
    input_p = Path(input_path)
    if not input_p.exists():
        raise InputFileNotFoundError(input_path)
    if not input_p.is_file():
        raise FileError(f"Input path is not a file: {input_path}")

    if input_p.suffix.lower() not in IMAGE_EXTS:
        raise UnsupportedFileTypeError(input_path, IMAGE_EXTS)

    if output_path is None:
        output_p = input_p.with_stem(f"{input_p.stem}_marked")
    else:
        output_p = Path(output_path)
        if output_p.suffix.lower() not in IMAGE_EXTS:
            raise InvalidOutputPathError(
                output_path,
                f"Output file extension must be one of {', '.join(sorted(list(IMAGE_EXTS)))}",
            )
        if output_p.is_dir():
            raise InvalidOutputPathError(output_path, "Output path cannot be a directory.")

    try:
        output_p.parent.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        raise InvalidOutputPathError(
            str(output_p), f"Could not create parent directory: {e}"
        ) from e

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
        max_chars = int((width - 2 * margin) / avg_char_width) if avg_char_width > 0 else 20
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

        img.save(str(output_p))

    except Exception as e:
        if isinstance(e, MarkerError):
            raise
        raise ImageMarkingError(f"An unexpected error occurred during image processing: {e}") from e