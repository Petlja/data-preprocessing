"""Make the `scripts` directory a package so `scripts.cli` is importable."""

__all__ = [
    "cli",
    "config",
    "directive_templates",
    "sources",
    "utils",
    "pandoc_filters",
]



import logging
from rich.logging import RichHandler

logger = logging.getLogger(__name__)

if not logger.hasHandlers():
    handler = RichHandler(show_time=False)
    formatter = logging.Formatter(' %(message)s')
    handler.setFormatter(formatter)
    logging.basicConfig(level=logging.INFO, handlers=[handler])
    
