import os
from typing import List, Optional
from pydantic import BaseModel, ValidationError
from scripts.utils import read_yaml
from logging import getLogger

logger = getLogger(__name__)

class Activity(BaseModel):
    type: Optional[str] = None
    title: Optional[str] = None
    file: Optional[str] = None
    description: Optional[str] = None
    guid: Optional[str] = None


class Lesson(BaseModel):
    title: Optional[str] = None
    folder: Optional[str] = None
    guid: Optional[str] = None
    description: Optional[str] = None
    activities: List[Activity] = []


class CourseIndex(BaseModel):
    courseId: Optional[str] = None
    lang: Optional[str] = None
    title: Optional[str] = None
    description: Optional[dict] = None
    lessons: List[Lesson] = []


def _load_index(yaml_path: str) -> CourseIndex:
    raw = read_yaml(yaml_path)
    try:
        idx = CourseIndex.model_validate(raw)
    except ValidationError:
        raise
    return idx


def collect_activity_files(repo_path: str) -> List[str]:
    index_path = os.path.join(repo_path, "_sources", "index.yaml")
    if os.path.exists(index_path):
        return _collect_from_petljadoc(index_path)
    source_index_path = os.path.join(repo_path, "source")
    if os.path.isdir(source_index_path):
        return _collect_from_plct(source_index_path)
    raise FileNotFoundError(f"No recognized index file found in repo: {repo_path}")

def convert_files(base_dir: str, files: List[str], output_dir: str) -> None:
    for src in files:
        rel_path = os.path.relpath(src, start=base_dir)
        dest = os.path.splitext(os.path.join(output_dir, rel_path))[0] + ".md"
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        _convert_file(src, dest)

def _collect_from_plct(plct_source_path) -> List[str]:
    found: List[str] = []
    for root, _, filenames in os.walk(plct_source_path):
        for filename in filenames:
            if filename.endswith((".md")) and not filename == "index.md":
                src = os.path.join(root, filename)
                found.append(src)
    return found

def _collect_from_petljadoc(index_path) -> List[str]:
    idx = _load_index(index_path)
    base_dir = os.path.dirname(index_path)
    found: List[str] = []

    for lesson in idx.lessons:
        for act in lesson.activities:
            if act.type not in ("reading", "quiz"):
                continue
            src = os.path.join(base_dir, lesson.folder, act.file)
            if os.path.exists(src) and os.path.isfile(src):
                found.append(src)
            else:
                logger.warning(f"Activity file not found: {src}")

    return found

class MissingPandocError(Exception):
    pass

def _convert_file(src: str, dest: str) -> None:
    """Convert using pypandoc."""
    try:
        import pypandoc
    except Exception:
        raise MissingPandocError("pypandoc not installed")
    filter_path = os.path.join('.', 'scripts', 'filter.py')
    logger.info(f"Converting {src} => {dest}")
    extra = ["--standalone=false", "--quiet"]
    if src.endswith(".md"):
        pypandoc.convert_file(src, to="md", format="md", extra_args=extra, outputfile=dest)
    elif src.endswith(".rst"):
        extra.append(f"--filter={filter_path}")
        pypandoc.convert_file(src, to="md", format="md", extra_args=extra, outputfile=dest)