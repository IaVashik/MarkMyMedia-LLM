import argparse
import os
import sys
import time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import defaultdict

from . import check_ffmpeg_available, mark_image, mark_audio, mark_video
from . import __version__
from .errors import MarkerError

DEFAULT_OUTPUT = "markered_modals"

# Supported extensions per modality
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".gif", ".tiff", ".tif", ".webp"}
AUDIO_EXTS = {".mp3", ".flac", ".aac", ".m4a", ".ogg", ".opus"}
VIDEO_EXTS = {".mp4", ".mov", ".avi", ".mkv", ".webm", ".mpg", ".mpeg"}

def print_progress(mod_label, processed_count, total_count):
    progress_message = f"⚙️  Processing {mod_label}: {processed_count}/{total_count}"
    print(progress_message, end='\r', flush=True)
    return progress_message

def gather_files(paths, recursive: bool, output_dir: Path):
    """
    Resolve input paths into a flat list of file paths, applying recursion if requested.
    """
    result = []
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
            if recursive:
                for f in p.rglob("*"):
                    if f.is_file():
                        result.append(f.resolve())
            else:
                for f in p.iterdir():
                    if f.is_file():
                        result.append(f.resolve())
        else:
            # Nonexistent path, skip with warning
            print(f"⚠️ Warning: input path does not exist and will be skipped: {p}", file=sys.stderr)
    return result


def categorize(files):
    """
    Split file list into image/audio/video buckets based on extension.
    Returns dict with modality -> list[Path]
    """
    buckets = {"photo": [], "audio": [], "video": [], "unknown": []}
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


def ensure_output_dir(base_output: Path):
    """
    Ensure the output base directory exists.
    """
    base_output.mkdir(parents=True, exist_ok=True)
    return base_output


def construct_output_path(input_path: Path, output_base: Path, modality: str, preserve_structure: bool):
    """
    Derive output path for each modality.
    If preserve_structure is True, it collocates outputs under output_base preserving relative structure.
    Otherwise, it places all files directly into output_base.
    """
    stem = input_path.stem
    ext = input_path.suffix

    if preserve_structure:
        # mirror directory tree under output_base
        target_dir = output_base / input_path.parent.relative_to(Path.cwd())
        target_dir.mkdir(parents=True, exist_ok=True)
    else:
        # flat output directory
        target_dir = output_base

    if modality == "photo":
        out_name = f"{stem}_marked{ext}"
    elif modality == "audio":
        out_name = f"{stem}.mp4"  # audio becomes mp4
    elif modality == "video":
        # preserve extension but append _marked before it
        out_name = f"{stem}_marked{ext}"
    else:
        out_name = f"{stem}_marked{ext}"

    return target_dir / out_name


def process_photo(path: Path, output_base: Path, preserve_structure: bool):
    out_path = construct_output_path(path, output_base, "photo", preserve_structure)
    try:
        mark_image(str(path), str(out_path))
        success = True
        error = None
    except MarkerError as e:
        success = False
        error = e
    return ("photo", path, out_path, success, error)


def process_audio(path: Path, output_base: Path, preserve_structure: bool):
    out_path = construct_output_path(path, output_base, "audio", preserve_structure)
    try:
        mark_audio(str(path), str(out_path))
        success = True
        error = None
    except MarkerError as e:
        success = False
        error = e
    return ("audio", path, out_path, success, error)


def process_video(path: Path, output_base: Path, preserve_structure: bool):
    out_path = construct_output_path(path, output_base, "video", preserve_structure)
    try:
        mark_video(str(path), str(out_path))
        success = True
        error = None
    except MarkerError as e:
        success = False
        error = e
    return ("video", path, out_path, success, error)


def run_pipeline(all_files, output_base: Path, jobs: int, preserve_structure: bool):
    """
    Execute processing in order: photos -> audio -> video, each with thread pooling.
    Returns collected results.
    """
    summary = []
    timings = {}  
    buckets = categorize(all_files)

    modality_order = [
        ("photo", "photos", process_photo),
        ("audio", "audio files", process_audio),
        ("video", "videos", process_video),
    ]

    for mod_name, mod_label, processor in modality_order:
        items = buckets.get(mod_name, [])
        if not items:
            continue

        total_count = len(items)
        processed_count = 0
        stage_start_time = time.perf_counter()
        
        # Thread pool per modality
        with ThreadPoolExecutor(max_workers=jobs) as exe:
            futures = {exe.submit(processor, f, output_base, preserve_structure): f for f in items}
            print_progress(mod_label, 0, total_count)

            for future in as_completed(futures):
                processed_count += 1
                progress_message = print_progress(mod_label, processed_count, total_count)

                # Collect the result as before.
                res = future.result()
                summary.append(res)
            stage_duration = time.perf_counter() - stage_start_time
            timings[mod_name] = stage_duration
        print(" " * (len(progress_message) + 5), end='\r')
        print(f"✅ Finished processing {total_count} {mod_label}.")


    if buckets.get("unknown"):
        print(f"⚠️ Skipped {len(buckets['unknown'])} unknown file type")

    return summary, timings


def format_summary(results, timings, output_base: Path):
    """
    Build and print human-readable summary from individual results.
    """
    total_files = len(results)
    counts = defaultdict(int)
    failures = []

    for modality, inp, outp, success, error in results:
        counts[modality] += 1
        if not success:
            failures.append((modality, inp, error))
    # Unicode box drawing for aesthetics
    print("\n📊 Process Summary:")
    print("────────────────")
    print(f"  Total Files: {total_files} files")
    for mod in ("photo", "video", "audio"):
        name = mod.capitalize()
        cnt = counts.get(mod, 0)
        t = timings.get(mod, 0.0)
        if cnt > 0:
            print(f"    - {name}: {cnt} files ({t:.2f} s)")
    print(f"  Output: {output_base.resolve()}")
    
    if failures:
        print("⚠️ Failures:")
        for modality, inp, error in failures:
            print(f"  - [{modality}] {inp}: {error}")
    
    print("\n🎉 All Done!")


def parse_args():
    parser = argparse.ArgumentParser(
        prog="markmymedia",
        description="Batch mark images, audio, and video with filename overlays."
    )
    parser.add_argument(
        "inputs",
        nargs="*",
        help="Files or directories to process. If omitted, current directory is used."
    )
    parser.add_argument(
        "-r", "--recursive",
        action="store_true",
        help="Recursively traverse directories."
    )
    parser.add_argument(
        "-o", "--output",
        type=str,
        default=DEFAULT_OUTPUT,
        help=f"Base output directory (default: {DEFAULT_OUTPUT})."
    )
    parser.add_argument(
        "-j", "--jobs",
        type=int,
        default=os.cpu_count() or 4,
        help="Number of worker threads to use per modality (default: number of CPUs)."
    )
    parser.add_argument(
        "-p", "--preserve-structure",
        action="store_true",
        help="Preserve the directory structure of input files in the output directory."
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}"
    )
    return parser.parse_args()


def main():
    check_ffmpeg_available() 
    args = parse_args()
    input_paths = args.inputs or ["."]
    output_base = Path(args.output)
    all_files = gather_files(input_paths, recursive=args.recursive, output_dir=output_base)
    if not all_files:
        print("No input files found to process.", file=sys.stderr)
        sys.exit(1)

    ensure_output_dir(output_base)

    start_total = time.perf_counter()
    results, timings = run_pipeline(
        all_files, 
        output_base, 
        jobs=args.jobs, 
        preserve_structure=args.preserve_structure
    )
    total_elapsed = time.perf_counter() - start_total

    format_summary(results, timings, output_base)
    print(f"  Total elapsed time: {total_elapsed:.2f} s")