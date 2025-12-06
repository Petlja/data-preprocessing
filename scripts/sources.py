import os
import re
import tempfile
from typing import List, Optional
from pydantic import BaseModel, ValidationError
from pypandoc import convert_file
from scripts.utils import read_str, read_yaml, write_str
from logging import getLogger

logger = getLogger(__name__)

extra_rst = [
    "--standalone=false",
    f"--filter={ os.path.join('.', 'scripts', 'pandoc_filters', 'filter_rst.py')}", 
    "--quiet"
    ]
extra_md = [
    "--standalone=false",
    f"--filter={ os.path.join('.', 'scripts', 'pandoc_filters', 'filter_md.py')}", 
    "--quiet"
    ]

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
    for source_file_path in files:
        rel_path = os.path.relpath(source_file_path, start=base_dir)
        extension = os.path.splitext(rel_path)[1].lower()[1:]
        output_file_path = os.path.splitext(os.path.join(output_dir, rel_path))[0] + ".md"
        os.makedirs(os.path.dirname(output_file_path), exist_ok=True)
        if extension == "md":
            updated = _preprocess_markdown_fences(source_file_path)
            write_str(output_file_path, updated)
            _convert_file(output_file_path, extension)
        if extension == "rst":
            updated = _preprocess_rst(source_file_path)
            write_str(output_file_path, updated)
            _convert_file(output_file_path, extension, output_file_path)

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

def _convert_file(src: str, extension: str = None, dest: str = None) -> None:
    if dest is None:
        dest = src
    extra = extra_md if extension == "md" else extra_rst
    logger.info("Converting %s => %s", src, dest)
    try:
        convert_file(src, to="md", format=extension, extra_args=extra, outputfile=dest)
    except OSError as e:
        logger.error("Pandoc not found when converting %s: %s", src, e)
        raise MissingPandocError("Pandoc is not installed or not on PATH") from e
    except Exception:
        logger.exception("Error converting %s => %s", src, dest)
        raise


def _preprocess_markdown_fences(src_path: str) -> str:
    src = read_str(src_path)
    regex_fence = r"(\s*)```{(\w+)}"

    updated_src = re.sub(regex_fence, r"\1```\2", src)
    return updated_src

def _preprocess_rst(src_path: str) -> str:
    src = read_str(src_path)
    regex_empty_lines = r"^[ \t\s]+$"
    updated_src = re.sub(regex_empty_lines, r"", src, flags=re.MULTILINE)
    return updated_src