import os
import re
import hashlib
from typing import Any, Dict, List, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
import unicodedata
from pydantic import BaseModel, ValidationError
from pypandoc import convert_file
from scripts.utils import read_str, read_yaml, write_json, write_str
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


def write_structure_json(base_dir: str, repo: str, output_dir: str) -> str:
    repo_path = os.path.join(base_dir, repo)
    index_path = os.path.join(repo_path, "_sources", "index.yaml")
    source_path = os.path.join(repo_path, "source")

    if os.path.exists(index_path):
        structure = _build_petljadoc_structure(index_path, base_dir, output_dir, repo)
        source_type = "petljadoc"
    elif os.path.isdir(source_path):
        structure = _build_plct_structure(source_path, base_dir, output_dir, repo)
        source_type = "plct"
    else:
        raise FileNotFoundError(f"No recognized index file found in repo: {repo_path}")

    output_repo_dir = os.path.join(output_dir, _normalize_filename(repo))
    os.makedirs(output_repo_dir, exist_ok=True)
    structure_path = os.path.join(output_repo_dir, "structure.json")

    payload = {
        "schema_version": 1,
        "book_id": repo,
        "source_type": source_type,
        "title": structure["title"],
        "sub_segments": structure["sub_segments"],
    }
    write_json(structure_path, payload)
    return structure_path

def convert_files(base_dir: str, repo: str, files: List[str], output_dir: str, max_workers: int) -> None:
    def _process_one(source_file_path: str) -> None:
        output_rel_path = _source_to_output_rel_path(base_dir, source_file_path)
        extension = os.path.splitext(source_file_path)[1].lower()[1:]
        repo_base_dir = os.path.join(os.path.abspath(base_dir), repo)
        output_file_path = os.path.join(output_dir, output_rel_path)
        
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


def _build_petljadoc_structure(index_path: str, base_dir: str, output_dir: str, repo: str) -> Dict[str, Any]:
    idx = _load_index(index_path)
    source_root = os.path.dirname(index_path)
    repo_title = idx.title or repo
    lessons: List[Dict[str, Any]] = []

    for lesson in idx.lessons:
        lesson_folder = lesson.folder or ""
        lesson_source_ref = os.path.join(source_root, lesson_folder)
        lesson_segment_id = lesson.guid or _segment_id_from_path(
            os.path.relpath(lesson_source_ref, start=base_dir),
        )

        lesson_node: Dict[str, Any] = {
            "segment_id": lesson_segment_id,
            "title": lesson.title or os.path.basename(lesson_folder) or "Untitled",
            "sub_segments": [],
        }

        for act in lesson.activities:
            if act.type not in ("reading", "quiz"):
                continue
            if not act.file:
                continue

            src = os.path.join(source_root, lesson_folder, act.file)
            if not os.path.exists(src) or not os.path.isfile(src):
                logger.warning("Activity file not found when building structure: %s", src)
                continue

            output_rel_path = _source_to_output_rel_path(base_dir, src).replace(os.sep, "/")
            activity_segment_id = act.guid or _segment_id_from_path(
                os.path.relpath(src, start=base_dir),
            )

            lesson_node["sub_segments"].append(
                {
                    "segment_id": activity_segment_id,
                    "title": act.title or _fallback_title_from_path(src),
                    "content_path": output_rel_path,
                    "sub_segments": [],
                }
            )

        lessons.append(lesson_node)

    return {"title": repo_title, "sub_segments": lessons}


def _build_plct_structure(source_root: str, base_dir: str, output_dir: str, repo: str) -> Dict[str, Any]:
    root_index = os.path.join(source_root, "index.md")
    visited: set[str] = set()

    if not os.path.exists(root_index):
        return {"title": repo, "sub_segments": []}

    root_title = _extract_markdown_title(root_index) or repo
    root_children: List[Dict[str, Any]] = []

    for child in _extract_toctree_targets(root_index):
        child_path = _resolve_toctree_target(os.path.dirname(root_index), child)
        if not child_path:
            continue
        node = _build_plct_node(child_path, source_root, base_dir, output_dir, visited)
        if node is not None:
            root_children.append(node)

    return {"title": root_title, "sub_segments": root_children}


def _build_plct_node(
    md_path: str,
    source_root: str,
    base_dir: str,
    output_dir: str,
    visited: set[str],
) -> Optional[Dict[str, Any]]:
    md_path = os.path.normpath(md_path)
    if md_path in visited:
        return None
    visited.add(md_path)

    if not os.path.exists(md_path) or not os.path.isfile(md_path):
        logger.warning("Missing toctree target while building structure: %s", md_path)
        return None

    rel_from_source = os.path.relpath(md_path, start=source_root).replace(os.sep, "/")
    segment_id = _segment_id_from_path(rel_from_source)

    if os.path.basename(md_path).lower() == "index.md":
        title = _extract_markdown_title(md_path) or _fallback_title_from_path(os.path.dirname(md_path))
        children: List[Dict[str, Any]] = []
        for child in _extract_toctree_targets(md_path):
            child_path = _resolve_toctree_target(os.path.dirname(md_path), child)
            if not child_path:
                continue
            child_node = _build_plct_node(child_path, source_root, base_dir, output_dir, visited)
            if child_node is not None:
                children.append(child_node)

        return {
            "segment_id": segment_id,
            "title": title,
            "sub_segments": children,
        }

    output_rel_path = _source_to_output_rel_path(base_dir, md_path).replace(os.sep, "/")
    return {
        "segment_id": segment_id,
        "title": _extract_markdown_title(md_path) or _fallback_title_from_path(md_path),
        "content_path": output_rel_path,
        "sub_segments": [],
    }


def _extract_toctree_targets(md_path: str) -> List[str]:
    src = read_str(md_path)
    blocks = re.findall(r"```\{toctree\}[^\n]*\n(.*?)```", src, flags=re.DOTALL)
    targets: List[str] = []

    for block in blocks:
        for raw_line in block.splitlines():
            line = raw_line.strip()
            if not line or line.startswith(":") or line.startswith("#"):
                continue
            if "<" in line and line.endswith(">"):
                line = line.rsplit("<", 1)[1][:-1].strip()
            targets.append(line)
    return targets


def _resolve_toctree_target(base_dir: str, target: str) -> Optional[str]:
    target = target.strip()
    if not target:
        return None

    target = target.replace("\\", "/")
    raw_path = os.path.normpath(os.path.join(base_dir, target))

    if os.path.isfile(raw_path):
        return raw_path

    if os.path.splitext(raw_path)[1]:
        return raw_path if os.path.isfile(raw_path) else None

    as_md = f"{raw_path}.md"
    as_index = os.path.join(raw_path, "index.md")

    if os.path.isfile(as_md):
        return as_md
    if os.path.isfile(as_index):
        return as_index
    return None


def _extract_markdown_title(md_path: str) -> Optional[str]:
    src = read_str(md_path)

    if src.startswith("---"):
        fm_end = src.find("\n---", 3)
        if fm_end != -1:
            src = src[fm_end + 4 :]

    for line in src.splitlines():
        m = re.match(r"^\s{0,3}#\s+(.+?)\s*$", line)
        if m:
            return m.group(1).strip().strip("#").strip()
    return None


def _source_to_output_rel_path(base_dir: str, source_file_path: str) -> str:
    rel_path = os.path.relpath(source_file_path, start=base_dir)
    parts = rel_path.split(os.sep)
    # Remove repository source folder components so archive paths don't include them
    parts = [p for p in parts if p not in ("source", "_sources")]
    safe_parts = [_normalize_filename(p) for p in parts]
    safe_rel_path = os.path.join(*safe_parts)
    return os.path.splitext(safe_rel_path)[0] + ".md"


def _segment_id_from_path(rel_path: str) -> str:
    normalized = rel_path.replace("\\", "/")
    digest = hashlib.sha1(normalized.encode("utf-8")).hexdigest()[:32]
    return f"{digest[:8]}-{digest[8:12]}-{digest[12:16]}-{digest[16:20]}-{digest[20:32]}"


def _fallback_title_from_path(path: str) -> str:
    base = os.path.basename(path)
    if not base:
        base = os.path.basename(os.path.dirname(path))
    stem = os.path.splitext(base)[0]
    return stem.replace("_", " ").strip() or "Untitled"

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
    # Replace non-standard code block classes with ones that Pandoc filters will recognize, and remove any language specifier after the class to prevent Pandoc from treating it as a code block language
    src = src.replace("py-code", "pycode").replace("db-query", "dbquery")
    regex_fence = r"(\s*)```{(\w+)}(\s+(\w+))?"
    updated_src = re.sub(regex_fence, r"\1```\2", src)
    return updated_src

def _preprocess_rst(src_path: str) -> str:
    src = read_str(src_path)
    # Strip asterisks from acsection markers so Pandoc won't parse them as emphasis
    src = re.sub(r"(#\s*)-\*-\s*(acsection:\s*\S+)\s*-\*-", r"# {\2}", src)
    # Remove lines that are only whitespace to prevent Pandoc from treating them as hard breaks
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