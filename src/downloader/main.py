import logging
import os
import re
import subprocess
import time
import uuid
from pathlib import Path
from typing import cast

import pandas as pd

from src.downloader.config import Config

ROOT = Path(os.getcwd())
config = Config()
logger = logging.getLogger(__name__)


def find_file_by_basename(base_path: Path) -> Path:
    matches = list(base_path.parent.glob(base_path.stem + ".*"))

    if len(matches) == 0:
        raise FileNotFoundError(f"No file found with basename: {base_path.stem}")
    if len(matches) > 1:
        raise FileExistsError(f"Multiple files found with basename: {base_path.stem}")

    return matches[0]


def ensure_directories():
    output_dir = ROOT / Config().get("output_dir")
    output_dir.mkdir(parents=True, exist_ok=True)
    temp_dir = ROOT / Config().get("temp_dir")
    temp_dir.mkdir(parents=True, exist_ok=True)


def gen_temp_file_path(suffix: str | None = None) -> Path:
    suffix = suffix or ""
    temp_dir = ROOT / Config().get("temp_dir")
    temp_file = temp_dir / f"{uuid.uuid4()}{suffix}"
    return temp_file


def format_cmd_with_config(cmd: list[str], extended_args: dict[str,str]) -> list[str]:
    format_args= Config().data
    format_args.update(extended_args)
    return [cmd_param.format(**format_args) for cmd_param in cmd]


def snake_case(text: str) -> str:
    text = re.sub(r'[^a-zA-Z0-9\s]', '', text.lower())
    text = re.sub(r'\s+', '_', text)
    return text


def download_file(url: str, output_path: Path):
    if not output_path.parent.exists():
        raise FileNotFoundError(f"Output directory does not exist: {output_path.parent}")

    if output_path.exists():
        raise FileExistsError(f"Output file already exists: {output_path}")

    formatted_download_cmd = format_cmd_with_config(
            config.get("download_cmd"),
            {"url": url, "output": str(output_path), "archive": config.get("archive_file")})
    subprocess.run(formatted_download_cmd, check=True)

    return find_file_by_basename(output_path)


def convert_to_opus(input_file_path: Path, output_file_path: Path):
    if input_file_path == output_file_path:
        raise ValueError("Input cannot be the same as output when converting to opus.")
    if not input_file_path.exists():
        raise FileNotFoundError(f"Input file does not exist: {input_file_path}")
    if output_file_path.exists():
        raise FileExistsError(f"Output file already exists: {output_file_path}")

    formatted_convert_cmd = format_cmd_with_config(
            config.get("convert_cmd"), 
            {"input": str(input_file_path), "output": str(output_file_path)})

    subprocess.run(formatted_convert_cmd, check=True)


def add_metadata(input_path: Path, output_path: Path, title: str, composer: str):
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
    ) for arg in config.get("metadata_cmd")]

    subprocess.run(
        formatted_metadata_command,
        check=True
    )


def process_row(row: pd.Series) -> None:
    url = cast(str,row["url"])
    title = cast(str,row["title"])
    author = cast(str,row["author"])
    output_stem = snake_case(f"{title} {author}")
    output_file_path = ROOT / Config().get("output_dir") / f"{output_stem}.opus"

    logger.info(f"Processing row: URL={url}, Title={title}, Author={author}, Output={output_file_path}")

    try:
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

    except Exception:
        logger.exception(f"Error processing row with URL {url}")

    # Sleep if configured
    if config.get("sleep", 0) > 0:
        time.sleep(config.get("sleep", 0))


def main():
    ensure_directories()
    input_file = ROOT / Config().get("input_file")
    df = pd.read_csv(input_file)

    if df.empty:
        logger.warning(f"No data found in input file: {input_file}")
        return

    df.apply(process_row, axis=1)

