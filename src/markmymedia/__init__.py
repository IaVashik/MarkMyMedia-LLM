"""
Top-level package for markmymedia: utilities to mark audio, image, and video files
with identifying overlays (filename, etc.).
"""

from __future__ import annotations

__version__ = "1.1.0"

# Public API exports
from .mark_audio import mark_audio
from .mark_image import mark_image
from .mark_video import mark_video
from .io import gather_files, categorize, construct_output_path
from .errors import MarkerError

__all__ = [
    "mark_audio",
    "mark_image",
    "mark_video",
    "check_ffmpeg_available",
    "gather_files",
    "categorize",
    "construct_output_path",
    "MarkerError",
    "__version__",
]

import shutil
import warnings


def check_ffmpeg_available() -> None:
    """Warn if ffmpeg or ffprobe are missing from PATH."""
    missing = []
    if shutil.which("ffmpeg") is None:
        missing.append("ffmpeg")
    if shutil.which("ffprobe") is None:
        missing.append("ffprobe")
    if missing:
        warnings.warn(
            f"The following external tools are not found in PATH: {', '.join(missing)}. "
            "Functionality may fail. Install them or adjust your PATH.",
            UserWarning,
        )