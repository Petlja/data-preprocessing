import os
import re
from typing import Any, Dict, List, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
import unicodedata
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

class MissingPandocError(Exception):
    pass

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

def convert_files(base_dir: str, repo: str, files: List[str], output_dir: str, max_workers: int) -> None:
    def _process_one(source_file_path: str) -> None:
        rel_path = os.path.relpath(source_file_path, start=base_dir)
        extension = os.path.splitext(rel_path)[1].lower()[1:]
        repo_base_dir = os.path.join(os.path.abspath(base_dir), repo)

        parts = rel_path.split(os.sep)
        # Remove repository source folder components so archive paths don't include them
        parts = [p for p in parts if p not in ("source", "_sources")]
        safe_parts = [_normalize_filename(p) for p in parts]
        safe_rel_path = os.path.join(*safe_parts)
        output_file_path = os.path.splitext(os.path.join(output_dir, safe_rel_path))[0] + ".md"
        
        os.makedirs(os.path.dirname(output_file_path), exist_ok=True)
        if extension == "md":
            updated = _preprocess_markdown_fences(source_file_path)
            write_str(output_file_path, updated)
            _convert_file(output_file_path, {"repo_base_dir": repo_base_dir}, "md", output_file_path)
        elif extension == "rst":
            updated = _preprocess_rst(source_file_path)
            write_str(output_file_path, updated)
            _convert_file(output_file_path, {"repo_base_dir": repo_base_dir}, "rst", output_file_path)
        else:
            logger.debug("Skipping unsupported extension %s for %s", extension, source_file_path)

    errors: List[Tuple[str, Exception]] = []

    if max_workers == 1:
        for src in files:
            try:
                _process_one(src)
            except Exception as e:
                logger.exception("Error converting %s", src)
                errors.append((src, e))
    else:
        with ThreadPoolExecutor(max_workers=max_workers) as exc:
            futures = {exc.submit(_process_one, src): src for src in files}
            for fut in as_completed(futures):
                src = futures[fut]
                try:
                    fut.result()
                except Exception as e:
                    logger.exception("Error converting %s", src)
                    errors.append((src, e))

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

def _convert_file(src: str, meta: Dict[str, Any], extension: str = None, dest: str = None) -> None:
    if dest is None:
        dest = src
    extra = list(extra_md if extension == "md" else extra_rst)
    for key, value in meta.items():
        extra.append(f"--metadata={key}={value}")

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
    src = src.replace("\py-code", "pycode").replace("db-query", "dbquery")
    regex_fence = r"(\s*)```{(\w+)}(\s+(\w+))?"
    updated_src = re.sub(regex_fence, r"\1```\2", src)
    return updated_src

def _preprocess_rst(src_path: str) -> str:
    src = read_str(src_path)
    regex_empty_lines = r"^[ \t\s]+$"
    updated_src = re.sub(regex_empty_lines, r"", src, flags=re.MULTILINE)
    return updated_src

def _normalize_filename(name: str, max_length: int = 255) -> str:
    if not name:
        return name

    translit = {
        'А':'A','Б':'B','В':'V','Г':'G','Д':'D','Ђ':'Dj','Е':'E','Ж':'Z','З':'Z','И':'I','Ј':'J','К':'K','Л':'L','Љ':'Lj','М':'M','Н':'N','Њ':'Nj','О':'O','П':'P','Р':'R','С':'S','Т':'T','Ћ':'C','У':'U','Ф':'F','Х':'H','Ц':'C','Ч':'C','Џ':'Dz','Ш':'S',
        'а':'a','б':'b','в':'v','г':'g','д':'d','ђ':'dj','е':'e','ж':'z','з':'z','и':'i','ј':'j','к':'k','л':'l','љ':'lj','м':'m','н':'n','њ':'nj','о':'o','п':'p','р':'r','с':'s','т':'t','ћ':'c','у':'u','ф':'f','х':'h','ц':'c','ч':'c','џ':'dz','ш':'s',
    }

    s = unicodedata.normalize('NFKD', name)

    s2_chars = []
    for ch in s:
        if ch in translit:
            s2_chars.append(translit[ch])
        else:
            if unicodedata.category(ch).startswith('M'):
                continue
            s2_chars.append(ch)
    s2 = ''.join(s2_chars)

    s2 = s2.replace(os.sep, '_')
    s2 = re.sub(r'[^A-Za-z0-9._\-]', '_', s2)
    s2 = re.sub(r'_+', '_', s2)

    s2 = s2.strip('_.')

    if len(s2) > max_length:
        s2 = s2[:max_length]

    if not s2:
        return 'file'
    return s2