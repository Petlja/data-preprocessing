
import re
import sys
from typing import Any, Optional, Dict, Callable, List
from pandocfilters import toJSONFilter, Div, Para, Str, walk, CodeBlock, RawBlock

from scripts.directive_templates import YOUTUBE_LINK
from scripts.pandoc_filters.filter_util import *


def filter(key, value, format, meta) -> Optional[dict[str, Any]]:
    if key == "Div":
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
        original_text = stringify_with_newlines(contents)

        handler = info.get("handler_rst")
        result = handler(parsed_kvs, original_text, contents, ident, classes, kvs)

        normalized = normalize_to_blocks(result)
        if normalized is None:
            return None

        return normalized
    return None
        

if __name__ == "__main__":
    toJSONFilter(filter)
