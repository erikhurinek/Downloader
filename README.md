# YT-DLP Wrapper for Downloading Music

This Python project downloads and extracts audio from various streaming sites.

## Installation and Execution

This project uses [uv](https://docs.astral.sh/uv/), a fast Python package manager.

1. Create and activate a Python virtual environment in the project root.

```bash
uv venv
source .venv/bin/activate
```

2. Install requirements.
```bash
uv sync
```

3. Populate `input.csv`. 
For example,
```csv
url,                             title, author
https://youtube.com/watch?v=..., Foo,   Bar
```

4. Execute the downloader.
```bash
uv run main.py
```

## Cleaning Up

By default, downloaded URLs are record in an archive text file, and future repeated downloads will be skipped.
If you wish to download the URL again, perform the following actions:

1. Delete the contents of the temporary directory. By default, this should be called `temp/` and will contain the archive file `archive.txt`.
2. Move or delete the contents of the output directory, `output/` by default.

## Configuration

The `config.json` file in the project root contains settings.
You can alter the commands used to download, convert, and write the metadata to media.

## Notes

Excessive downloads may result in temporary blocks from the media provider.
Avoid downloading the same media in rapid succession.
A `sleep` parameter is provided in `config.json` to wait between downloads.
