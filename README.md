# MarkMyMedia

[![PyPI version](https://img.shields.io/pypi/v/MarkMyMedia.svg)](https://pypi.org/project/MarkMyMedia/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A fast, simple utility to visually stamp media files with their filenames, preparing them for multimodal LLM training and analysis.

## The Problem: Lost Context in Multimodal Sequences

When you feed a sequence of media files (e.g., `cat.jpg`, `intro.mp3`, `dog_on_beach.mp4`) to a Large Language Model, the model sees a continuous stream of data. It lacks explicit, built-in separators or context about where one file ends and another begins, or what the original source of a particular frame or soundbite was.

This ambiguity makes it difficult to:
-   Analyze which specific file triggered a response.
-   Train the model on tasks that require knowledge of file boundaries.
-   Debug model behavior on complex, mixed-media inputs.

## The Solution: Visibly Embedded Markers

**MarkMyMedia** solves this by "stamping" each file with its own name, creating an unambiguous visual or auditory marker directly within the data.

-   **Images:** Get a clean text overlay with the filename.
-   **Audio:** Are converted into a video with the filename displayed on a black background.
-   **Videos:** Get a short, 0.5-second marker clip prepended, showing the filename without re-encoding the entire video.

This way, the context is never lost. The model "sees" the filename associated with the content that follows.

## Key Features

-   **Multimodal Support:** Works out-of-the-box for images, audio, and video.
-   **Blazing Fast:** Uses parallel processing to handle large datasets quickly.
-   **Efficient Video Processing:** Prepends markers to videos **without re-encoding**, saving massive amounts of time and preserving original quality.
-   **Flexible Usage:** Can be used as a simple command-line tool or as a Python library.
-   **Recursive Search:** Point it at a directory, and it can process all nested media files.
-   **Simple & Focused:** Does one job and does it well.

## Prerequisites

This tool relies on **FFmpeg** for all audio and video operations. You must have `ffmpeg` and `ffprobe` installed and available in your system's PATH.

-   **Official Site:** [ffmpeg.org](https://ffmpeg.org/download.html)
-   **On macOS (via Homebrew):** `brew install ffmpeg`
-   **On Debian/Ubuntu:** `sudo apt update && sudo apt install ffmpeg`
-   **On Arch:** C'mon, you've already established it for sure :P

## Installation

Install `MarkMyMedia` directly from PyPI:

```bash
pip install MarkMyMedia
```

## Usage

### As a Command-Line Tool (CLI)

The CLI is designed for batch processing entire directories.

**Mark all media in the current directory (output to `markered_modals/`):**
```bash
markmymedia 
```

**Recursively process a dataset and specify an output folder:**
```bash
markmymedia ./my_dataset -r -o ./processed_data
```

**See all available options:**
`markmymedia --help`
```
usage: markmymedia [-h] [-r] [-o OUTPUT] [-j JOBS] [-p] [--version] [inputs ...]

Batch mark images, audio, and video with filename overlays.

positional arguments:
  inputs                Files or directories to process. If omitted, current directory is used.

options:
  -h, --help            show this help message and exit
  -r, --recursive       Recursively traverse directories.
  -o, --output OUTPUT   Base output directory (default: markered_modals).
  -j, --jobs JOBS       Number of worker threads to use per modality (default: number of CPUs).
  -p, --preserve-structure
                        Preserve the directory structure of input files in the output directory.
  --version             show program's version number and exit

```

### As a Python Library

You can also use the core functions directly in your Python scripts for more granular control.

```python
from markmymedia import mark_image, mark_audio, mark_video

# Mark a single image
mark_image(
    input_path='data/cat.jpg',
    output_path='processed/cat_marked.jpg'
)

# Create a marked video from an audio file
mark_audio(
    input_path='data/intro.mp3',
    output_path='processed/intro.mp4'
)

# Prepend a marker to a video file
mark_video(
    input_path='data/dog_on_beach.mp4',
    output_path='processed/dog_on_beach.mp4',
    overlay_text="Some cool video!!",
)
```

## Contributing

Contributions are welcome! If you find a bug or have a feature request, please [open an issue](https://github.com/IaVashik/MarkMyMedia-LLM/issues).

## License

This project is licensed under the MIT License. See the `LICENSE` file for details.