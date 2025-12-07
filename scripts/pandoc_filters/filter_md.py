
from typing import Any, Optional, Dict, List
from pandocfilters import toJSONFilter
import re

from filter_util import DIRECTIVES, normalize_to_blocks

def filter(key, value, format, meta) -> Optional[dict[str, Any]]:
    opt_re = re.compile(r":(\w+):\s*(.*)")
    if key == "CodeBlock":
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
    return None
        

if __name__ == "__main__":
    toJSONFilter(filter)
