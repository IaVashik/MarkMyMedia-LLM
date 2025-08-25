import sys
from pathlib import Path
from typing import List, Dict, Literal

from .errors import InputFileNotFoundError
from .formats import IMAGE_EXTS, AUDIO_EXTS, VIDEO_EXTS


def gather_files(
    paths: List[Path],
    recursive: bool,
    output_dir: Path,
) -> List[Path]:
    """
    Resolve input paths into a flat list of file paths, applying recursion if requested.

    Args:
        paths (List[Path]): A list of file or directory paths to process.
        recursive (bool): If True, traverses directories recursively.
        output_dir (Path): The base output directory, which will be excluded from the search.

    Returns:
        List[Path]: A list of resolved, absolute file paths.

    Raises:
        InputFileNotFoundError: If a path in `paths` does not exist.
    """
    result: List[Path] = []
    resolved_exclude_path = output_dir.resolve()

    if not paths:
        paths = [Path(".")]

    for p in paths:
        p = Path(p)
        if p.resolve() == resolved_exclude_path:
            continue
        if p.is_file():
            result.append(p.resolve())
        elif p.is_dir():
            glob_pattern = "**/*" if recursive else "*"
            for f in p.glob(glob_pattern):
                if f.is_file():
                    result.append(f.resolve())
        else:
            raise InputFileNotFoundError(str(p))                
    return result


def categorize(files: List[Path]) -> Dict[str, List[Path]]:
    """
    Split a file list into image, audio, and video buckets based on extension.

    Args:
        files (List[Path]): A list of file paths.

    Returns:
        Dict[str, List[Path]]: A dictionary mapping modality ('photo', 'audio', 'video', 'unknown')
                               to a list of corresponding file paths.
    """
    buckets: Dict[str, List[Path]] = {
        "photo": [],
        "audio": [],
        "video": [],
        "unknown": [],
    }
    for f in files:
        ext = f.suffix.lower()
        if ext in IMAGE_EXTS:
            buckets["photo"].append(f)
        elif ext in AUDIO_EXTS:
            buckets["audio"].append(f)
        elif ext in VIDEO_EXTS:
            buckets["video"].append(f)
        else:
            buckets["unknown"].append(f)
    return buckets


def construct_output_path(
    input_path: Path,
    output_base: Path,
    modality: str,
    preserve_structure: bool,
    source_base: Path = None,
) -> Path:
    """
    Derive the output path for a given input file.

    Args:
        input_path (Path): The path to the source file.
        output_base (Path): The root directory for all output files.
        modality (str): The type of media ('photo', 'audio', 'video').
        preserve_structure (bool): If True, the relative directory structure from `source_base`
                                   to `input_path` is recreated under `output_base`.
        source_base (Path, optional): The root of the source file tree, used for preserving
                                      structure. Defaults to the current working directory.

    Returns:
        Path: The calculated absolute path for the output file.
    """
    stem = input_path.stem
    ext = input_path.suffix

    if preserve_structure:
        base = source_base or Path.cwd()
        try:
            relative_dir = input_path.parent.relative_to(base)
            target_dir = output_base / relative_dir
        except ValueError:
            # Fallback if input_path is not under base, place it in the root
            target_dir = output_base
    else:
        target_dir = output_base

    target_dir.mkdir(parents=True, exist_ok=True)

    if modality == "photo":
        out_name = f"{stem}_marked{ext}"
    elif modality == "audio":
        out_name = f"{stem}.mp4"
    elif modality == "video":
        out_name = f"{stem}_marked{ext}"
    else:
        # Fallback for unknown types, though categorize() should prevent this.
        out_name = f"{stem}_marked{ext}"

    return target_dir / out_name