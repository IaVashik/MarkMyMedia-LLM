import os
import subprocess
from typing import Tuple
from pathlib import Path

from .errors import (
    AudioMarkingError, 
    InputFileNotFoundError, 
    FFmpegNotFoundError, 
    FFmpegProcessError, 
    InvalidMediaError,
    MarkerError,
    UnsupportedFileTypeError,
    InvalidOutputPathError,
    FileError,
)
from .formats import AUDIO_EXTS
from .utils import _generate_lavfi_drawtext


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
        output_path (str, optional): Output video path. Must have a .mp4 extension.
        resolution (tuple): Video resolution (width, height).

    Raises:
        InputFileNotFoundError: If the input file does not exist.
        UnsupportedFileTypeError: If the input file is not a supported audio format.
        InvalidOutputPathError: If the specified output path is invalid.
        AudioMarkingError: On any other processing failure.
    """
    input_p = Path(input_path)
    if not input_p.exists():
        raise InputFileNotFoundError(input_path)
    if not input_p.is_file():
        raise FileError(f"Input path is not a file: {input_path}")
    
    if input_p.suffix.lower() not in AUDIO_EXTS:
        raise UnsupportedFileTypeError(input_path, AUDIO_EXTS)
    
    if output_path is None:
        output_p = input_p.with_suffix(".mp4")
    else:
        output_p = Path(output_path)
        if output_p.suffix.lower() != ".mp4":
            raise InvalidOutputPathError(output_path, "Output file for marked audio must be an .mp4 file.")
        if output_p.is_dir():
            raise InvalidOutputPathError(output_path, "Output path cannot be a directory.")

    try:
        output_p.parent.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        raise InvalidOutputPathError(
            str(output_p), f"Could not create parent directory: {e}"
        ) from e

    if overlay_text is None:
        overlay_text = "Filename: " + os.path.basename(input_path)
    lavfi_source = _generate_lavfi_drawtext(overlay_text, resolution)
    
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
        str(output_p)
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
        if isinstance(e, MarkerError):
            raise
        raise AudioMarkingError(f"An unexpected error occurred during audio marking: {e}") from e