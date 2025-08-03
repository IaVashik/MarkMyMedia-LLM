
import os
import subprocess
from typing import Tuple

from .errors import (
    AudioMarkingError, 
    InputFileNotFoundError, 
    FFmpegNotFoundError, 
    FFmpegProcessError, 
    InvalidMediaError
)
from .utils import _generate_lavfi_drawtext

COPY_SAFE_CONTAINERS = {"mp3", "m4a", "ogg", "aac", "flac", "m4a", "opus"}

def mark_audio(
    input_path: str,
    output_path: str = None,
    resolution: Tuple[int, int] = (1280, 256),
    overlay_text: str = None,
) -> None:
    """
    Overlay file name text on a black background and combine with audio to produce a video.

    Args:
        input_path (str): Path to the input audio file.
        output_path (str, optional): Output video path. Defaults to same name with .mp4.
        resolution (tuple): Video resolution (width, height).

    Raises:
        AudioMarkingError: On any processing failure.
    """
    if not os.path.exists(input_path):
        raise InputFileNotFoundError(input_path)

    if output_path is None:
        base, _ = os.path.splitext(input_path)
        output_path = f"{base}.mp4"

    if overlay_text is None:
        overlay_text = "Filename: " + os.path.basename(input_path)
    lavfi_source = _generate_lavfi_drawtext(overlay_text, resolution)
    
    ext = os.path.splitext(input_path)[1].lower().lstrip('.')
    if ext not in COPY_SAFE_CONTAINERS:
        raise InvalidMediaError(f"Container '{ext}' is not suitable for audio stream copying.")

    ffmpeg_cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", lavfi_source,
        "-i", input_path,
        "-framerate", "1",
        "-map", "0:v:0",
        "-map", "1:a:0",
        "-c:v", "libx264",
        "-crf", "20",
        "-pix_fmt", "yuv420p",
        "-c:a", "copy",
        output_path
    ]

    try:
        subprocess.run(
            ffmpeg_cmd, 
            check=True, 
            stdout=subprocess.DEVNULL, 
            stderr=subprocess.STDOUT
        )
    except FileNotFoundError:
        raise FFmpegNotFoundError()
    except subprocess.CalledProcessError as e:
        raise FFmpegProcessError(command=ffmpeg_cmd, stderr=e.stderr) from e
    except Exception as e:
        raise AudioMarkingError(f"An unexpected error occurred during audio marking: {e}") from e