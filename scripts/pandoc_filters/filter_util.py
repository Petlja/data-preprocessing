
from typing import List
from typing import Any, Optional, Dict, List
from pandocfilters import Div, Para, Str, walk, CodeBlock, RawBlock
from directive_templates import YOUTUBE_LINK

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
    return Div([ident, ["reveal"], []], contents)

def ytpopup_handler(options: Dict[str, Any], original_text: str, contents: List[Any], ident: str, classes: List[str], kvs: List[Any]) -> Any:
    html = YOUTUBE_LINK.format(video_id=options.get("id", ""))
    return Div([ident, ["text"], []], [RawBlock("html", html)])

def activecode_handler(options: Dict[str, Any], original_text: str, contents: List[Any], ident: str, classes: List[str], kvs: List[Any]) -> Any:
    return CodeBlock([ident, ["activecode"], []], original_text)

def default_handler(options: Dict[str, Any], original_text: str, contents: List[Any], ident: str, classes: List[str], kvs: List[Any]) -> None:
    return original_text

def karel_handler(options: Dict[str, Any], original_text: str, contents: List[Any], ident: str, classes: List[str], kvs: List[Any]) -> Any:
    return CodeBlock([ident, ["karel"], []], original_text)

# Central directives registry: each entry can specify whether it expects an id and an optional handler.
DIRECTIVES: Dict[str, Dict[str, Any]] = {
    "mchoice": {"has_id": True, "handler_rst": default_handler, "handler_md": default_handler},
    "fitb": {"has_id": True, "handler_rst": default_handler, "handler_md": default_handler},
    "parsons": {"has_id": True, "handler_rst": default_handler, "handler_md": default_handler},
    "dragndrop": {"has_id": True, "handler_rst": default_handler, "handler_md": default_handler},
    "ytpopup": {"has_id": True, "handler_rst": ytpopup_handler, "handler_md": default_handler},
    "karel": {"has_id": True, "handler_rst": karel_handler, "handler_md": default_handler},
    "activecode": {"has_id": True, "handler_rst": activecode_handler, "handler_md": default_handler},
    "questionnote": {"has_id": False, "handler_rst": notes_handler, "handler_md": notes_handler},
    "suggestionnote": {"has_id": False, "handler_rst": notes_handler, "handler_md": notes_handler},
    "technicalnote": {"has_id": False, "handler_rst": notes_handler, "handler_md": notes_handler},
    "infonote": {"has_id": False, "handler_rst": notes_handler, "handler_md": notes_handler},
    "learnmorenote": {"has_id": False, "handler_rst": notes_handler, "handler_md": notes_handler},
    "reveal" : {"has_id": True, "handler_rst": reveal_handler, "handler_md": default_handler},
}


def normalize_to_blocks(result: Optional[Any]) -> Optional[List[Any]]:
    if result is None:
        return None
    if isinstance(result, str):
        return [Para([Str(result)])]
    if isinstance(result, list):
        return result
    return result