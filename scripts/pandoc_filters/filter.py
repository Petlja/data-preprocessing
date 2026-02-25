from typing import Any, Optional, Dict, List
from pandocfilters import toJSONFilter
import re

from filter_util import DIRECTIVES, normalize_to_blocks, stringify_with_newlines


opt_re = re.compile(r":(\w+):\s*(.*)")


def _handle_codeblock(value, meta) -> Optional[List[Any]]:
    [[ident, classes, kvs], code] = value

    cb_class = classes[0] if classes else ""
    info = DIRECTIVES.get(cb_class)
    if not info:
        return None

    # filter out options from code block content
    parsed_kvs: Dict[str, str] = {}
    new_code_lines: List[str] = []
    for line in code.splitlines():
        m = opt_re.match(line)
        if m:
            parsed_kvs[m.group(1)] = m.group(2)
        else:
            new_code_lines.append(line)

    original_text = "\n".join(new_code_lines)

    handler = info.get("handler_md")
    result = handler(parsed_kvs, original_text, code, ident, classes, kvs)

    normalized = normalize_to_blocks(result)
    if normalized is None:
        return None

    return normalized


def _handle_div(value, meta) -> Optional[List[Any]]:
    [[ident, classes, kvs], contents] = value
    div_class = classes[0] if classes else ""

    info = DIRECTIVES.get(div_class)
    if not info:
        return None

    if info.get("has_id") and contents:
        id = stringify_with_newlines(contents[0])
        contents = contents[1:]
        kvs.append(["id", id])

    parsed_kvs = {k: v for k, v in kvs}
    parsed_kvs["repo_base_dir"] = meta.get("repo_base_dir", {}).get("c", "")
    original_text = stringify_with_newlines(contents)

    handler = info.get("handler_rst")
    result = handler(parsed_kvs, original_text, contents, ident, classes, kvs)

    normalized = normalize_to_blocks(result)
    if normalized is None:
        return None

    return normalized


def filter(key, value, format, meta) -> Optional[dict[str, Any]]:
    if key == "CodeBlock":
        return _handle_codeblock(value, meta)
    if key == "Div":
        return _handle_div(value, meta)
    return None


if __name__ == "__main__":
    toJSONFilter(filter)
