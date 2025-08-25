import subprocess
import os
from typing import Tuple
import tempfile
import uuid
from pathlib import Path

from fractions import Fraction

from .errors import (
    MarkerError,
    VideoMarkingError,
    InputFileNotFoundError,
    InvalidMediaError,
    FFmpegNotFoundError,
    FFmpegProcessError,
    UnsupportedFileTypeError,
    InvalidOutputPathError,
    FileError,
)
from .formats import VIDEO_EXTS
from .utils import _ffprobe_param, _generate_lavfi_drawtext

def mark_video(
    input_path: str,
    output_path: str = None,
    resolution: Tuple[int, int] = None,
    overlay_text: str = None,
) -> None:
    """
    Prepend a 0.5-second marker (black frame + filename text) to an existing video,
    without re-encoding the original video/audio streams (only the marker).

    Args:
        input_path (str): path to source video file.
        output_path (str, optional): path to result video.
        resolution (tuple, optional): override (width, height). By default taken from input.

    Raises:
        InputFileNotFoundError: If the input file does not exist.
        UnsupportedFileTypeError: If the input file is not a supported video format.
        InvalidOutputPathError: If the specified output path is invalid.
        InvalidMediaError: If the video's codecs are not supported for stream copying.
        VideoMarkingError: on any other failure.
    """
    input_p = Path(input_path)
    if not input_p.exists():
        raise InputFileNotFoundError(input_path)
    if not input_p.is_file():
        raise FileError(f"Input path is not a file: {input_path}")

    if input_p.suffix.lower() not in VIDEO_EXTS:
        raise UnsupportedFileTypeError(input_path, VIDEO_EXTS)
    
    if output_path is None:
        output_p = input_p.with_stem(f"{input_p.stem}_marked")
    else:
        output_p = Path(output_path)
        if output_p.suffix.lower() not in VIDEO_EXTS:
            raise InvalidOutputPathError(
                output_path,
                f"Output file extension must be one of {', '.join(sorted(list(VIDEO_EXTS)))}",
            )
        if output_p.is_dir():
            raise InvalidOutputPathError(output_path, "Output path cannot be a directory.")
            
    try:
        output_p.parent.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        raise InvalidOutputPathError(
            str(output_p), f"Could not create parent directory: {e}"
        ) from e
        
    marker_container = None
    marker_ts = None
    main_ts = None

    try:
        try:
            probe = _ffprobe_param(input_path)
        except FFmpegProcessError as e:
            raise VideoMarkingError("Failed to probe video parameters.") from e
        
        streams = probe.get("streams", [])
        if not streams:
            raise InvalidMediaError("No media streams found in the input file.")

        # first video stream
        video_stream = next((s for s in streams if s.get("codec_type") == "video"), None)
        if not video_stream:
            raise InvalidMediaError("No video stream found in the input file.")

        width = resolution[0] if resolution else int(video_stream.get("width", 0))
        height = resolution[1] if resolution else int(video_stream.get("height", 0))
        if width <= 0 or height <= 0:
            raise InvalidMediaError(f"Invalid video resolution detected: {width}x{height}.")

        fps_str = video_stream.get("r_frame_rate", "30/1")
        try:
            fps = str(Fraction(fps_str))
        except Exception:
            fps = fps_str # fallback

        video_codec = video_stream.get("codec_name", "").lower()
        if video_codec not in ("h264", "hevc"):
            raise InvalidMediaError(f"Unsupported video codec: '{video_codec}'. Only h264/hevc are supported for stream copying.")

        # audio stream (if any)
        audio_stream = next((s for s in streams if s.get("codec_type") == "audio"), None)
        if audio_stream:
            audio_codec = audio_stream.get("codec_name", "").lower()
            if audio_codec not in (None, "", "aac"):
                raise InvalidMediaError(f"Unsupported audio codec: '{audio_codec}'. Only AAC or no audio is supported for stream copying.")
            
        # unique temporary files
        tmp = tempfile.gettempdir()
        uid = uuid.uuid4().hex
        marker_container = os.path.join(tmp, f"marker_{uid}.mp4")
        marker_ts = os.path.join(tmp, f"marker_{uid}.ts")
        main_ts = os.path.join(tmp, f"main_{uid}.ts")

        if overlay_text is None:
            overlay_text = "Filename: " + os.path.basename(input_path)
        video_encoder = "libx264" if video_codec == "h264" else "libx265"

        lavfi_src = _generate_lavfi_drawtext(overlay_text, (width, height), 0.5)
        # create the marker: video + silent audio (so that the concatenated file has an audio stream if the original does)
        cmd_marker = [
            "ffmpeg", "-y",
            "-f", "lavfi", "-i", lavfi_src,
            "-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=44100",
            "-shortest",
            "-c:v", video_encoder,
            "-pix_fmt", "yuv420p",  # compatible, sufficient for the marker
            "-r", fps,
            "-c:a", "aac", "-ar", "44100",
            marker_container
        ]
        subprocess.run(cmd_marker, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)

        # remux both fragments into MPEG-TS with the required bitstream filter
        v_bsf = "h264_mp4toannexb" if video_codec == "h264" else "hevc_mp4toannexb"
        for src, dst in ((marker_container, marker_ts), (input_path, main_ts)):
            cmd = [
                "ffmpeg", "-y",
                "-i", src,
                "-c", "copy",
                "-bsf:v", v_bsf,
                "-f", "mpegts",
                dst
            ]
            subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)

        # final concat
        concat_input = f"concat:{marker_ts}|{main_ts}"
        final_cmd = [
            "ffmpeg", "-y",
            "-i", concat_input,
            "-c", "copy"
        ]
        # if outputting to mp4 and AAC audio is present, apply a filter for correct packaging
        if str(output_p).lower().endswith(".mp4"):
            final_cmd += ["-bsf:a", "aac_adtstoasc"]
        final_cmd.append(str(output_p))
        subprocess.run(final_cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)

    except subprocess.CalledProcessError as e:
        raise FFmpegProcessError(command=e.cmd, stderr=e.stderr.decode('utf-8', 'ignore')) from e
    except (VideoMarkingError, InvalidMediaError, FFmpegNotFoundError):
        raise
    except Exception as e:
        if isinstance(e, MarkerError):
            raise
        raise VideoMarkingError(f"An unexpected error occurred during marking: {e}") from e
    finally:
        for p in (marker_container, marker_ts, main_ts):
            if p and os.path.exists(p):
                try:
                    os.remove(p)
                except OSError:
                    pass