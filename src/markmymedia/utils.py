import json
import subprocess
import textwrap
from typing import Tuple, Optional

from .errors import FFmpegProcessError

def _wrap_text(text: str, max_chars_per_line: int) -> str:
    """Wrap text into lines with maximum character width."""
    return "\n".join(textwrap.wrap(text, width=max_chars_per_line))


def _generate_lavfi_drawtext(text: str, resolution: Tuple[int, int], duration: Optional[float]  = 1) -> str:
    """
    Generate FFmpeg lavfi source with wrapped text for drawtext.
    """
    width, height = resolution
    avg_char_width = 30
    max_chars = max(1, width // avg_char_width)

    wrapped = _wrap_text(text, max_chars)
    escaped = wrapped.replace(":", "\\:").replace("'", "\\'")

    drawtext = (
        f"text='{escaped}':"
        f"x=(w-text_w)/2:"
        f"y=(h-text_h)/2:"
        f"fontcolor=white:"
        f"fontsize=40:"
        f"box=1:boxcolor=0x000000B0:boxborderw=10"
    )

    return f"color=c=black:s={width}x{height}:d={duration},drawtext={drawtext}"

def _ffprobe_param(input_path: str) -> dict:
    """
    Run ffprobe to extract a single stream parameter.
    entry: e.g. 'width', 'height', 'r_frame_rate'
    """
    cmd = [
        "ffprobe", "-v", "error",
        "-select_streams", "v:0",
        "-show_streams",
        "-print_format", "json",
        input_path
    ]
    try:
        result = subprocess.run(cmd, check=True, stdout=subprocess.PIPE, text=True)
        return json.loads(result.stdout)
    except subprocess.CalledProcessError as e:
        raise FFmpegProcessError(command=cmd, stderr=e.stderr) from e
