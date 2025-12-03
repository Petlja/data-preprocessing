# data-preprocessing

Tools to fetch and lightly preprocess Sphinx-based documentation repositories.

**Project goals**
- **Fetch repositories**: clone or update repositories listed in `config.json`.
- **Detect project type**: identify the Sphinx project type (if applicable).
- **Extract sources**: collect activity/source files referenced in `_sources/index.yaml` or `source/index.md`and convert them to normalized Markdown.

## Quick start (Poetry)

- Install Poetry (if needed):

```powershell
pip install poetry
```

- Install project dependencies and create the environment:

```powershell
poetry install
```

## Quick start (no Poetry)

- Install runtime dependencies into your active Python environment:

```powershell
pip install -r requirements.txt
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

Notes:
- Ensure `pandoc` is available (use `get-pandoc` to install if needed).

