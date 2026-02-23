import sys
import click
import os 

from git import Repo, GitCommandError
from pydantic_core import ValidationError
from scripts.config import is_git_repo, load_config
from scripts.sources import MissingPandocError, collect_activity_files, convert_files
from logging import getLogger

logger = getLogger(__name__)

@click.group()
def cli():
    """Project helper CLI."""


@cli.command("git-sync")
@click.option("--config", default="config.json", show_default=True, help="Path to config.json")
@click.option("--base-dir", default="repos", show_default=True, help="Base directory to store repositories")
def git_sync(config, base_dir):
    """Clone or pull repositories listed in a config.json file.

    The config file should be a JSON object with a top-level "repos" array. Each item
    may be either a string (the repo URL) or an object with keys `url` and optional `path`.
    """

    if not os.path.exists(config):
        logger.error(f"Config file not found: {config}")
        sys.exit(1)
    try:
        conf = load_config(config)
    except ValidationError as e:
        logger.error(f"Invalid config file: {e}")
        sys.exit(1)
    if not conf.repos:
        logger.info("No repositories found in config.")
        sys.exit(0)

    os.makedirs(base_dir, exist_ok=True)

    for entry in conf.repos:
        url = entry.url
        name = os.path.splitext(os.path.basename(url.rstrip('/')))[0]
        target = os.path.join(base_dir, name)

        try:
            if is_git_repo(target):
                logger.info(f"Updating existing repo: {target}, pulling latest changes...")
                repo = Repo(target)
                origin = repo.remotes.origin
                origin.fetch()
                origin.pull()
            elif os.path.exists(target):
                logger.warning(f"Target exists but is not a git repo, skipping: {target}")
            else:
                logger.info(f"Cloning {url} into {target}")
                Repo.clone_from(url, target)
                logger.info(f"Cloned {name}")
        except GitCommandError as e:
            logger.error(f"Git error for {url}: {e}", exc_info=True)
        except Exception as e:
            logger.error(f"Error handling {url}: {e}", exc_info=True)


@cli.command("prepare-dataset")
@click.option("--base-dir", default="repos", show_default=True, help="Base directory repositories are stored in")
@click.option("--output-dir", default="dataset", show_default=True, help="Output directory for the prepared dataset")
@click.option("--jobs", type=click.IntRange(1), default=os.cpu_count(), show_default=True, help="Number of worker threads: 1 = serial; default is number of CPUs")
def prepare_dataset(base_dir, output_dir, jobs):
    """Prepare dataset by converting activity files from repositories into markdown format."""
    os.makedirs(output_dir, exist_ok=True)

    if not os.path.exists(base_dir):
        logger.error(f"Base directory not found: {base_dir}.")
        sys.exit(1)

    for repo in os.listdir(base_dir):
        repo_path = os.path.join(base_dir, repo)
        if is_git_repo(repo_path):
            logger.info(f"Preparing dataset from repo: {repo_path}")
            try:
                files = collect_activity_files(repo_path)
            except FileNotFoundError as e:
                logger.error(str(e))
                sys.exit(1)

            if not files:
                logger.error("No activity files found in index.")
                return
            try:
                max_workers = jobs
                if max_workers == 1:
                    logger.info("Converting files serially (1 worker)")
                elif max_workers > 1:
                    logger.info(f"Converting files in parallel using {max_workers} workers...")
                convert_files(base_dir, repo, files, output_dir, max_workers=max_workers)
            except MissingPandocError as e:
                logger.error(f"Runtime error: {e}")
                sys.exit(1)
            except Exception as e:
                logger.error(f"Error converting files from {repo_path}: {e}", exc_info=True)
            
        else:
            logger.warning(f"Skipping non-repo directory: {repo_path}")

@cli.command("get-pandoc")
def get_pandoc():
    """Download and install pandoc if not already installed."""
    try:
        from pypandoc.pandoc_download import download_pandoc
        from pypandoc import get_pandoc_version
        try:
            version = get_pandoc_version()
            logger.info(f"Pandoc is already installed, version: {version}")
        except OSError:
            download_pandoc()
    except Exception as e:
        logger.error(f"Error installing pandoc: {e}", exc_info=True)
        sys.exit(1)


@cli.command("bootstrap")
@click.option("--config", default="config.json", show_default=True, help="Path to config.json")
@click.option("--base-dir", default="repos", show_default=True, help="Base directory to store repositories")
@click.option("--output-dir", default="dataset", show_default=True, help="Output directory for the prepared dataset")
@click.option("--jobs", type=click.IntRange(1), default=os.cpu_count(), show_default=True, help="Number of worker threads for dataset preparation (1 = serial).")
def bootstrap(config, base_dir, output_dir, jobs):
    """Convenience command: install pandoc, sync repos, and prepare dataset."""
    try:
        gp = get_pandoc.callback if hasattr(get_pandoc, "callback") else get_pandoc
        gp()

        gs = git_sync.callback if hasattr(git_sync, "callback") else git_sync
        gs(config=config, base_dir=base_dir)

        pd = prepare_dataset.callback if hasattr(prepare_dataset, "callback") else prepare_dataset
        pd(base_dir=base_dir, output_dir=output_dir, jobs=jobs)
    except Exception as e:
        logger.error("Bootstrap failed: %s", e, exc_info=True)
        sys.exit(1)

def main():
    """Console-script entry point for packaging tools."""
    return cli()


if __name__ == "__main__":
    main()
