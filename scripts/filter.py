import re
from typing import Any, Optional
from pandocfilters import toJSONFilter, RawBlock

directive_re = re.compile(
    r'^\.\.\s+([a-zA-Z0-9_-]+)::?(.*)$',
    flags=re.DOTALL | re.MULTILINE,
)

def rst_directive_to_fenced(raw_rst: str) -> Optional[str]:
    m = directive_re.match(raw_rst.strip())
    if not m:
        return None

    name = m.group(1)
    body = raw_rst.split("::", 1)[1].lstrip(":\n ")

    fenced = f"```{{{name}}}\n{body}\n```"
    return fenced

def filter(key, value, _, __) -> Optional[dict[str, Any]]:
    if key == "RawBlock":
        lang, content = value
        if lang == "rst":
            result = rst_directive_to_fenced(content)
            if result:
                return RawBlock("markdown", result)

    return None

if __name__ == "__main__":
    toJSONFilter(filter)
