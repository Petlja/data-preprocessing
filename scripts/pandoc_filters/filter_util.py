import os
import re
from typing import List
from typing import Any, Optional, Dict, List
from pandocfilters import Div, Para, Str, walk, CodeBlock, RawBlock
from directive_templates import YOUTUBE_LINK
from scripts.utils import read_str



def _read_include(repo_root: str, include_path: str) -> Optional[str]:
    if not repo_root or not include_path:
        return None
    include_file = os.path.join(repo_root, include_path)
    if os.path.isfile(include_file):
        return read_str(include_file)
    return None


ACSECTION_RE = re.compile(r"^\s*#\s*-[-*]*\s*acsection:.*$")

def _clean_activecode(original_text: str) -> Dict[str, str]:
    text_part = ""
    code_part = ""
    hidden_part = ""

    if "~~~~" in original_text:
        text_part, rest = original_text.split("~~~~", 1)
    else:
        rest = original_text

    if "====" in rest:
        code_part, hidden_part = rest.split("====", 1)
    else:
        code_part = rest

    code_lines = [
        line for line in code_part.splitlines()
        if not ACSECTION_RE.match(line)
    ]

    return {
        "text": text_part.strip(),
        "code": "\n".join(code_lines).strip(),
        "hidden": hidden_part.strip(),
    }

def stringify_with_newlines(x: Any) -> str:
    result: List[str] = []

    def go(key, val, format, meta):
        if key == 'Str':
            result.append(val)
        elif key == 'Emph' or key == 'Strong' or key == 'Underline' or key == 'Strikeout':
            walk(val, go, format, meta)
        elif key == 'Code':
            result.append(val[1])
        elif key == 'Math':
            result.append(val[1])
        elif key == 'LineBreak':
            result.append("\n")
        elif key == 'SoftBreak':
            result.append("\n")
        elif key == 'Space':
            result.append(" ")
        elif key == 'DefinitionList':
            result.append("\n")

    walk(x, go, "", {})
    return ''.join(result)

def notes_handler(options: Dict[str, Any], original_text: str, contents: List[Any], ident: str, classes: List[str], kvs: List[Any]) -> str:
    return original_text.strip()

def reveal_handler(options: Dict[str, Any], original_text: str, contents: List[Any], ident: str, classes: List[str], kvs: List[Any]) -> Any:
    return Div([ident, [""], []], contents)

def ytpopup_handler(options: Dict[str, Any], original_text: str, contents: List[Any], ident: str, classes: List[str], kvs: List[Any]) -> Any:
    html = YOUTUBE_LINK.format(video_id=options.get("id", ""))
    return Div([ident, ["text"], []], [RawBlock("html", html)])

def activecode_handler(options: Dict[str, Any], original_text: str, contents: List[Any], ident: str, classes: List[str], kvs: List[Any]) -> Any:
    repo_root = options.pop("repo_base_dir", "")
    parts = _clean_activecode(original_text)
    hidden = parts["hidden"]
    # Resolve file includes: just repo_root + relative path
    for key in ("includesrc", "includexsrc", "includehsrc"):
        if key in options and options[key]:
            raw = _read_include(repo_root, options[key])
            if raw is not None:
                lines = [l for l in raw.splitlines() if not ACSECTION_RE.match(l)]
                hidden += "\n".join(lines).strip()
                break

    blocks: List[Any] = []

    if parts["text"]:
        blocks.append(Para([Str(parts["text"])]))

    if parts["code"]:
        blocks.append(Para([Str("Код који ученик види у едитору:")]))
        blocks.append(CodeBlock([ident, [], []], parts["code"]))
    
    if hidden:
        blocks.append(Para([Str("Код који ученик не види:")]))
        blocks.append(CodeBlock([ident, ["hidden"], []], hidden))

    return blocks if blocks else ""

def default_handler(options: Dict[str, Any], original_text: str, contents: List[Any], ident: str, classes: List[str], kvs: List[Any]) -> None:
    return original_text

def default_handler_md(options: Dict[str, Any], original_text: str, contents: List[Any], ident: str, classes: List[str], kvs: List[Any]) -> None:
    return Div([ident, classes, kvs], [Para([Str(original_text.strip())])])

def karel_handler(options: Dict[str, Any], original_text: str, contents: List[Any], ident: str, classes: List[str], kvs: List[Any]) -> Any:
    return CodeBlock([ident, ["karel"], []], original_text)

def quizq_handler(options: Dict[str, Any], original_text: str, contents: List[Any], ident: str, classes: List[str], kvs: List[Any]) -> Any:
    return Div([ident, [""], []], contents)

def mchoice_handler(options: Dict[str, Any], original_text: str, contents: List[Any], ident: str, classes: List[str], kvs: List[Any]) -> str:
    correct_raw = options.get("correct", "")
    correct_letters = {c.strip().lower() for c in correct_raw.split(",") if c.strip()}

    lines: List[str] = []
    if original_text.strip():
        lines.append(original_text.strip())
    lines.append("")

    for letter in "abcde":
        key = f"answer_{letter}"
        if key in options:
            lines.append(f"{letter}) {options[key]}")
        
    if correct_letters:
        lines.append("")
        lines.append(f"Тачан одговор(и): {', '.join(sorted(correct_letters))}")

    return "\n".join(lines)



def dragndrop_handler(options: Dict[str, Any], original_text: str, contents: List[Any], ident: str, classes: List[str], kvs: List[Any]) -> str:
    lines: List[str] = []
    if original_text.strip():
        lines.append(original_text.strip())
    lines.append("")

    for i in range(1, 21):
        key = f"match_{i}"
        if key in options:
            pair_parts = options[key].split("|||")
            if len(pair_parts) == 2:
                lines.append(f"- {pair_parts[0].strip()} → {pair_parts[1].strip()}")
            else:
                lines.append(f"- {options[key].strip()}")

    return "\n".join(lines)


def parsonsprob_handler(options: Dict[str, Any], original_text: str, contents: List[Any], ident: str, classes: List[str], kvs: List[Any]) -> str:
    parts = original_text.split("-----")
    lines: List[str] = []

    if len(parts) >= 1:
        question = parts[0].strip()
        if question:
            lines.append(question)
            lines.append("")

    if len(parts) >= 2:
        items = [item.strip() for item in parts[1].strip().splitlines() if item.strip()]
        lines.append("Исправан редослед:")
        for idx, item in enumerate(items, 1):
            lines.append(f"{idx}. {item}")

    return "\n".join(lines)


def fillintheblank_handler(options: Dict[str, Any], original_text: str, contents: List[Any], ident: str, classes: List[str], kvs: List[Any]) -> str:

    def collect_definition_groups(node: Any) -> List[List[Dict[str, Any]]]:
        groups: List[List[Dict[str, Any]]] = []
        def _collect_from_deflist(deflist_node: Dict[str, Any]) -> List[Dict[str, Any]]:
            items: List[Dict[str, Any]] = []
            first = True
            for term, defs in deflist_node.get('c', []):
                pattern = stringify_with_newlines(term).strip()
                is_incorrect = (bool(pattern) and pattern.lstrip().lower().startswith('x')) or not first
                first = False
                feedbacks: List[str] = []
                for d in defs:
                    txt = stringify_with_newlines(d).strip()
                    if txt:
                        feedbacks.append(txt)
                items.append({'pattern': pattern, 'feedbacks': feedbacks, 'incorrect': is_incorrect})
            return items

        if isinstance(node, dict):
            if node.get('t') == 'DefinitionList':
                groups.append(_collect_from_deflist(node))
            else:
                for child in node.get('c', []):
                    groups.extend(collect_definition_groups(child))
        elif isinstance(node, list):
            for item in node:
                groups.extend(collect_definition_groups(item))

        return groups

    def node_contains_definition(node: Any) -> bool:
        return bool(collect_definition_groups(node))

    question_parts: List[str] = []
    for elem in contents:
        if node_contains_definition(elem):
            break
        s = stringify_with_newlines(elem).strip()
        if s:
            question_parts.append(s)

    question_text = "\n".join(question_parts).strip()

    groups = collect_definition_groups(contents)

    lines: List[str] = []
    if question_text:
        lines.append(question_text)

    for idx, group in enumerate(groups, start=1):
        accepted = [d for d in group if not d.get('incorrect')]
        incorrect_entries = [d for d in group if d.get('incorrect')]

        # Label each blank when there are multiple
        if len(groups) > 1:
            lines.append("")
            lines.append(f"Одговор {idx}:")

        if accepted:
            lines.append("")
            lines.append("Тачни одговор(и):")
            for d in accepted:
                pat = d.get('pattern', '').strip()
                fbs = d.get('feedbacks', [])
                if fbs:
                    lines.append(f"- {pat} -> {' | '.join(fbs)}")
                else:
                    lines.append(f"- {pat}")

        if incorrect_entries:
            lines.append("")
            lines.append("Поруке за погрешан одговор:")
            for d in incorrect_entries:
                fbs = d.get('feedbacks', [])
                if fbs:
                    for fb in fbs:
                        lines.append(f"- {fb}")
                else:
                    pat = d.get('pattern', '').strip()
                    lines.append(f"- (непозната порука за погрешан унос: {pat})")

    structured = "\n".join(lines).strip()

    return structured if structured else original_text.strip()


def mchoice_handler_md(options: Dict[str, Any], original_text: str, contents: List[Any], ident: str, classes: List[str], kvs: List[Any]) -> str:
    """Handle mchoice blocks from MD sources (answer1, answer2, … keys; correct is comma-separated indices)."""
    correct_raw = options.get("correct", "")
    correct_indices = {c.strip() for c in correct_raw.split(",") if c.strip()}

    lines: List[str] = []
    if original_text.strip():
        lines.append(original_text.strip())
    lines.append("")

    for i in range(1, 21):
        key = f"answer{i}"
        if key in options:
            lines.append(f"{i}) {options[key]}")

    if correct_indices:
        lines.append("")
        lines.append(f"Тачан одговор(и): {', '.join(sorted(correct_indices))}")

    return "\n".join(lines)


def fitb_handler_md(options: Dict[str, Any], original_text: str, contents: List[Any], ident: str, classes: List[str], kvs: List[Any]) -> str:
    answer_raw = options.get("answer", "")

    text = original_text.strip()
    blank_counter = 0
    def _replace_blank(m):
        nonlocal blank_counter
        blank_counter += 1
        return f"{{Одговор {blank_counter}}}"
    text = re.sub(r"\|blank\|", _replace_blank, text)

    lines: List[str] = []
    if text:
        lines.append(text)

    if answer_raw:
        answers = [a.strip() for a in answer_raw.split(",") if a.strip()]
        lines.append("")
        for i, ans in enumerate(answers, 1):
                lines.append(f"Одговор {i}: {ans}")

    return "\n".join(lines)


def pycode_handler_md(options: Dict[str, Any], original_text: str, contents: List[Any], ident: str, classes: List[str], kvs: List[Any]) -> Any:
    """Output py-code blocks as plain Python code blocks."""
    return CodeBlock([ident, ["python"], []], original_text.strip())


def notes_handler_md(options: Dict[str, Any], original_text: str, contents: List[Any], ident: str, classes: List[str], kvs: List[Any]) -> Any:
    """Keep notes wrapped in a fenced Div so the note type is preserved."""
    return Para([Str(original_text.strip())])


# Central directives registry: each entry can specify whether it expects an id and an optional handler.
DIRECTIVES: Dict[str, Dict[str, Any]] = {
    "mchoice": {"has_id": True, "handler_rst": mchoice_handler, "handler_md": mchoice_handler_md},
    "fillintheblank": {"has_id": True, "handler_rst": fillintheblank_handler, "handler_md": fitb_handler_md},
    "fitb": {"has_id": True, "handler_rst": fillintheblank_handler, "handler_md": fitb_handler_md},
    "parsonsprob": {"has_id": True, "handler_rst": parsonsprob_handler, "handler_md": parsonsprob_handler},
    "dragndrop": {"has_id": True, "handler_rst": dragndrop_handler, "handler_md": dragndrop_handler},
    "ytpopup": {"has_id": True, "handler_rst": ytpopup_handler, "handler_md": default_handler_md},
    "karel": {"has_id": True, "handler_rst": karel_handler, "handler_md": default_handler_md},
    "activecode": {"has_id": True, "handler_rst": activecode_handler, "handler_md": default_handler_md},
    "questionnote": {"has_id": False, "handler_rst": notes_handler, "handler_md": notes_handler_md},
    "suggestionnote": {"has_id": False, "handler_rst": notes_handler, "handler_md": notes_handler_md},
    "technicalnote": {"has_id": False, "handler_rst": notes_handler, "handler_md": notes_handler_md},
    "infonote": {"has_id": False, "handler_rst": notes_handler, "handler_md": notes_handler_md},
    "learnmorenote": {"has_id": False, "handler_rst": notes_handler, "handler_md": notes_handler_md},
    "reveal" : {"has_id": True, "handler_rst": reveal_handler, "handler_md": default_handler_md},
    "quizq": {"has_id": False, "handler_rst": quizq_handler, "handler_md": default_handler_md},
    "pycode": {"has_id": True, "handler_rst": default_handler, "handler_md": pycode_handler_md},
    "dbquery": {"has_id": True, "handler_rst": default_handler, "handler_md": default_handler_md},
}


def normalize_to_blocks(result: Optional[Any]) -> Optional[List[Any]]:
    if result is None:
        return None
    if isinstance(result, str):
        return [Para([Str(result)])]
    if isinstance(result, list):
        return result
    return result