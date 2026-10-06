import os
import re
import subprocess
import time
import uuid
from pathlib import Path
from typing import cast

import pandas as pd
from tqdm import tqdm

from src.downloader.config import Config
from src.downloader.logger import Logger

ROOT = Path(os.getcwd())
COMMAND_TIMEOUT = 7200
PROGRESS_BAR_NAME = "Downloading media"


def find_file_by_basename(base_path: Path) -> Path:
    """
    Finds a file by base name, returning the path with extension.

    Raises an exception of zero or multiple matches were found.
    """
    matches = list(base_path.parent.glob(base_path.stem + ".*"))

    if len(matches) == 0:
        raise FileNotFoundError(f"No file found with basename: {base_path.stem}")
    if len(matches) > 1:
        raise FileExistsError(f"Multiple files found with basename: {base_path.stem}")

    return matches[0]


def ensure_config_directories() -> None:
    """
    Ensures temp and output directories exist.
    """
    output_dir = ROOT / Config.get("output_dir")
    output_dir.mkdir(parents=True, exist_ok=True)
    temp_dir = ROOT / Config.get("temp_dir")
    temp_dir.mkdir(parents=True, exist_ok=True)


def gen_temp_file_path(suffix: str | None = None) -> Path:
    """
    Generates a temporary file with an optional suffix (extension).
    """
    suffix = suffix or ""
    temp_dir = ROOT / Config.get("temp_dir")
    temp_file = temp_dir / f"{uuid.uuid4()}{suffix}"
    return temp_file


def format_cmd_with_config(cmd: list[str], extended_args: dict[str,str]) -> list[str]:
    """
    Formats a command using the current config parameters and any extended args.
    For example `mycommand {input_file}` would become `mycommand input.csv`.
    """
    format_args = Config.data()
    format_args.update(extended_args)
    return [cmd_param.format(**format_args) for cmd_param in cmd]


def snake_case(text: str) -> str:
    """
    Removes non-alphanumeric characters, and substitutes spaces with underscores.
    """
    text = re.sub(r'[^a-zA-Z0-9\s]', '', text.lower())
    text = re.sub(r'\s+', '_', text)
    return text


def download_file(url: str, output_path: Path) -> Path:
    """
    Downloads an audio file using the config's `download_cmd`.
    Returns the path of the downloaded file.
    """
    if not output_path.parent.exists():
        raise FileNotFoundError(f"Output directory not exist: {output_path.parent}")
    if output_path.exists():
        raise FileExistsError(f"Output file already exists: {output_path}")

    formatted_download_cmd = format_cmd_with_config(
            Config.get("download_cmd"),
            {"url": url, "output": str(output_path), "archive": Config.get("archive_file")})

    result = subprocess.run(formatted_download_cmd, check=True, capture_output=True, text=True, timeout=COMMAND_TIMEOUT)
    Logger.debug_process_result(result, label="Download")

    return find_file_by_basename(output_path)


def convert_to_opus(input_file_path: Path, output_file_path: Path) -> None:
    """
    Converts an input file to OPUS using the config's `convert_cmd`.
    """
    if input_file_path == output_file_path:
        raise ValueError("Input cannot be the same as output when converting to opus.")
    if not input_file_path.exists():
        raise FileNotFoundError(f"Input file does not exist: {input_file_path}")
    if output_file_path.exists():
        raise FileExistsError(f"Output file already exists: {output_file_path}")

    formatted_convert_cmd = format_cmd_with_config(
            Config.get("convert_cmd"), 
            {"input": str(input_file_path), "output": str(output_file_path)})

    result = subprocess.run(formatted_convert_cmd, check=True, capture_output=True, text=True, timeout=COMMAND_TIMEOUT)
    Logger.debug_process_result(result, label="Convert")


def add_metadata(input_path: Path, output_path: Path, title: str, composer: str) -> None:
    """
    Adds metadata using config's `metadata_cmd`.
    """
    if input_path == output_path:
        raise ValueError("Input cannot be the same as output when adding metadata.")
    if not input_path.exists():
        raise FileNotFoundError(f"Input file does not exist: {input_path}")
    if output_path.exists():
        raise FileExistsError(f"Output file already exists: {output_path}")

    formatted_metadata_command = [arg.format(
        input=str(input_path),
        output=str(output_path),
        title=title,
        author=composer
    ) for arg in Config.get("metadata_cmd")]

    result = subprocess.run(
        formatted_metadata_command,
        check=True,
        capture_output=True,
        text=True,
        timeout=COMMAND_TIMEOUT
    )
    Logger.debug_process_result(result, label="Metadata")


def process_row(row: pd.Series) -> None:
    """Processes a row, and therefore URL, in the CSV file."""
    url = cast(str,row["url"])
    title = cast(str,row["title"])
    author = cast(str,row["author"])
    output_stem = snake_case(f"{title} {author}")
    output_file_path = ROOT / Config.get("output_dir") / f"{output_stem}.opus"

    Logger.debug(f"Processing row: URL={url}, Title={title}, Author={author}, Output={output_file_path}")

    try:
        # Download the file
        temp_file_path = gen_temp_file_path()
        downloaded_file_path = download_file(url, temp_file_path)

        # Convert to OPUS if necessary
        converted_file_path = downloaded_file_path
        if downloaded_file_path.suffix.lower() != ".opus":
            opus_file_path = gen_temp_file_path(".opus")
            convert_to_opus(downloaded_file_path, opus_file_path)
            converted_file_path = opus_file_path
            
        # Add metadata
        add_metadata(converted_file_path, output_file_path, title, author)

        # Clean up temporary files
        temp_file_path.unlink(missing_ok=True)

    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
        Logger.error(f"Error processing row: URL={url}, Title={title}, Author={author}\n{e}")

    # Sleep if configured
    if Config.get("sleep", 0) > 0:
        time.sleep(Config.get("sleep", 0))


def main() -> None:
    """Main entry procedure."""
    ensure_config_directories()
    input_file = ROOT / Config.get("input_file")
    df = pd.read_csv(input_file)

    if df.empty:
        Logger.info(f"No data found in input file: {input_file}")
        return

    tqdm.pandas(desc=PROGRESS_BAR_NAME)
    df.progress_apply(process_row, axis=1)

