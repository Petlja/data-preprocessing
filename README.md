# PLCT AI Data Unifier Runner

Minimal runner wrapper for:
https://github.com/Petlja/PLCT-AI-Data-Unifier

This repository is intentionally small. It uses the package above as a dependency
and only provides a local config and one batch entry point for Windows users.

## What this runner does

- Reads repositories from plct-ai-data-unifier-config.yaml.
- Uses uv to install and lock dependencies from pyproject.toml.
- Runs the PLCT AI Data Unifier command flow.
- Keeps generated output on disk after the run is finished.

## Configuration

Edit plct-ai-data-unifier-config.yaml and keep your repository list under:

```yaml
repos:
  - url: https://github.com/Petlja/example-repo
```

You can include as many repos as needed.

## Run

1. Install uv.
2. Edit plct-ai-data-unifier-config.yaml.
3. Run run-au.bat.

Default run is full bootstrap and produces reusable output folders.

## Batch script modes

run-au.bat [config-file] [mode] [base-dir] [output-dir] [jobs]

Supported modes:
- bootstrap
- git-sync
- prepare-dataset

Examples:

- Full run (default values)
  run-au.bat

- Full run with explicit config and serial conversion
  run-au.bat plct-ai-data-unifier-config.yaml bootstrap repos dataset 1

- Only sync repositories
  run-au.bat plct-ai-data-unifier-config.yaml git-sync repos

- Only build dataset from already synced repositories
  run-au.bat plct-ai-data-unifier-config.yaml prepare-dataset repos dataset 4

Equivalent direct uv commands (same as package README, without batch wrapper):

```powershell
uv sync
uv run plct-ai-data-unifier bootstrap --config plct-ai-data-unifier-config.yaml --base-dir repos --output-dir dataset --jobs 1

# or step by step
uv run plct-ai-data-unifier git-sync --config plct-ai-data-unifier-config.yaml --base-dir repos
uv run plct-ai-data-unifier prepare-dataset --base-dir repos --output-dir dataset --jobs 1
```

## Output folders are preserved

After a successful run, folders are kept so users can continue to work with the
result without rerunning everything:

- repos
- dataset

No cleanup is performed by run-au.bat.

