# data-preprocessing

Tools to fetch and lightly preprocess Sphinx-based documentation repositories.

**Project goals**
- **Fetch repositories**: clone or update repositories listed in `config.json`.
- **Detect project type**: identify the Sphinx project type (if applicable).
- **Extract sources**: collect activity/source files referenced in `_sources/index.yaml` or `source/index.md`and convert them to normalized Markdown.

## Setup

If you use Poetry (recommended):

```powershell
# Install Poetry if needed
pip install poetry

# Install dependencies and create the virtual environment
poetry install

# Run the bootstrap command (installs pandoc, syncs repos, prepares dataset)
python -m scripts.cli bootstrap --config config.json --base-dir repos --output-dir dataset
```

If you prefer venv + pip:

```powershell
# Create and activate a venv
python -m venv .venv
.\.venv\Scripts\activate.bat

# Install runtime dependencies
pip install -r requirements.txt

# Run the bootstrap command
python -m scripts.cli bootstrap --config config.json --base-dir repos --output-dir dataset
```


## Commands

### `get-pandoc`

Installs Pandoc (using `pypandoc`) if it is not already available, or reports the installed version.

Basic usage:

```powershell
python -m scripts.cli get-pandoc
```

Options examples:


### `git-sync`

Clone or update repositories listed in a `config.json` file.

Basic usage:

```powershell
python -m scripts.cli git-sync
```

Options examples:

```powershell
python -m scripts.cli git-sync --config my-config.json  # use alternate config file
python -m scripts.cli git-sync --base-dir repos         # change repos directory
```

The config file is a JSON object with a top-level `repos` array. Each item may be either a string (the repo URL) or an object with keys `url` and optional `path`.

Example `config.json`:

```json
{
  "repos": [
    { "url": "https://example.com/repo1.git" },
    { "url": "https://example.com/repo2.git" }
  ]
}
```

### `prepare-dataset`

Convert activity/source files from each repository into a normalized Markdown dataset. This command detects the project type (when possible), collects the list of files from `_sources/index.yaml` or `_sources/index.md`, and converts them to Markdown using Pandoc.

Basic usage:

```powershell
python -m scripts.cli prepare-dataset
```

Options examples:

```powershell
python -m scripts.cli prepare-dataset --base-dir repos --output-dir dataset
```

Additional options:

- `--jobs`: control the number of worker threads for conversions. Use `--jobs 1` to force single-threaded (serial) conversion; omit the option to use the default (number of CPUs), or pass `--jobs N` to use `N` workers explicitly.

Examples:

```powershell
# Force serial conversion (useful for debugging or on constrained systems)
python -m scripts.cli prepare-dataset --base-dir repos --output-dir dataset --jobs 1

# Use the default number of workers (number of CPUs)
python -m scripts.cli prepare-dataset --base-dir repos --output-dir dataset

# Use 4 workers explicitly
python -m scripts.cli prepare-dataset --base-dir repos --output-dir dataset --jobs 4
```

Notes:
- Ensure `pandoc` is available (use `get-pandoc` to install if needed).

### `bootstrap`

Convenience command that runs the full local setup flow: ensures Pandoc is installed, syncs repositories listed in `config.json`, then prepares the dataset by converting activity files into normalized Markdown.

Basic usage:

```powershell
python -m scripts.cli bootstrap
```

Options examples:

```powershell
python -m scripts.cli bootstrap --config my-config.json --base-dir repos --output-dir dataset
```

What it does:
- Runs `get-pandoc` (installs Pandoc via `pypandoc` if missing).
- Runs `git-sync` to clone or update repositories from `config.json` into `--base-dir`.
- Runs `prepare-dataset` to collect activity files and convert them into markdown under `--output-dir`.

Notes:
- Useful for initial environment setup on a fresh machine or CI job.
- The command calls the same underlying code as the three individual commands, so you can still run steps separately when you need more control.
 
Notes about parallel conversions:

- The `bootstrap` command forwards the `--jobs` option to `prepare-dataset`. If you experience issues with parallel pandoc conversions or pandoc filters, retry with `--jobs 1` to run conversions serially.

Example (force serial conversion during bootstrap):

```powershell
python -m scripts.cli bootstrap --config my-config.json --base-dir repos --output-dir dataset --jobs 1
```

