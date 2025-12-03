"""Make the `scripts` directory a package so `scripts.cli` is importable."""

__all__ = ["cli", "convert_rst_to_md", "filter", "utils"]



import logging
from rich.logging import RichHandler

logger = logging.getLogger(__name__)

if not logger.hasHandlers():
    handler = RichHandler(show_time=False)
    formatter = logging.Formatter(' %(message)s')
    handler.setFormatter(formatter)
    logging.basicConfig(level=logging.INFO, handlers=[handler])
    
