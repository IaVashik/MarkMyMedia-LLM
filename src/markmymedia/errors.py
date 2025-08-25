class MarkerError(Exception):
    """Base exception for all errors in the markmymedia package."""
    pass


class FileError(MarkerError):
    """Base exception for file system related errors."""
    pass


class InputFileNotFoundError(FileError):
    """Raised when an input file does not exist."""
    def __init__(self, path: str):
        self.path = path
        super().__init__(f"Input file not found: {path}")


class InvalidOutputPathError(FileError):
    """Raised for issues with a specified output path."""
    def __init__(self, path: str, reason: str):
        self.path = path
        self.reason = reason
        super().__init__(f"Invalid output path: '{path}'. Reason: {reason}")


class DependencyError(MarkerError):
    """Base exception for missing external dependencies."""
    pass


class FFmpegNotFoundError(DependencyError):
    """Raised when the ffmpeg or ffprobe executable is not found in PATH."""
    def __init__(self, executable_name: str = "ffmpeg/ffprobe"):
        self.executable_name = executable_name
        message = (
            f"{executable_name} not found in PATH. "
            "Please ensure it is installed and accessible to the program."
        )
        super().__init__(message)


class FFmpegProcessError(DependencyError):
    """Raised when an FFmpeg or ffprobe process returns a non-zero exit code."""
    def __init__(self, command: list[str], stderr: str | None = None):
        self.command = command
        self.stderr = stderr
        cmd_str = " ".join(f"'{arg}'" if " " in arg else arg for arg in command)
        message = f"A subprocess call to FFmpeg failed.\nCommand: {cmd_str}"
        if stderr:
            message += f"\nDetails: {stderr.strip()}"
        super().__init__(message)


class MediaProcessingError(MarkerError):
    """Base exception for errors during the media marking process."""
    pass


class UnsupportedFileTypeError(MediaProcessingError):
    """Raised when an input file's type is not supported for the operation."""
    def __init__(self, path: str, supported_formats: set[str]):
        self.path = path
        self.supported_formats = supported_formats
        try:
            ext = path.split('.')[-1]
            msg_ext = f"'.{ext}'"
        except IndexError:
            msg_ext = "with no extension"

        super().__init__(
            f"File type {msg_ext} is not supported for this operation. "
            f"Supported formats are: {', '.join(sorted(list(supported_formats)))}"
        )


class AudioMarkingError(MediaProcessingError):
    """Raised for a general failure during audio processing."""
    pass


class ImageMarkingError(MediaProcessingError):
    """Raised for a general failure during image processing."""
    pass


class VideoMarkingError(MediaProcessingError):
    """Raised for a general failure during video processing."""
    pass


class InvalidMediaError(MediaProcessingError):
    """
    Raised for issues with media properties (e.g., codecs, streams, format)
    that make it unsuitable for processing.
    """
    pass