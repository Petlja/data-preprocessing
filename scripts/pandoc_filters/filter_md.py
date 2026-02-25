
from pandocfilters import toJSONFilter

from filter import filter as pandoc_filter


if __name__ == "__main__":
    toJSONFilter(pandoc_filter)
