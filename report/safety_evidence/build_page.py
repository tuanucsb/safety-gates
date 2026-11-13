"""Turn the readable page source into the three documents the dashboard stores.

The dashboard keeps its page in its own store as files/index.html, files/page.css and files/page.js. This script
derives those from report/safety_evidence/index.html (the readable single-file source) so that what is stored can
be regenerated and compared: comments are dropped, whitespace is collapsed and attributes are single-quoted, which
keeps each document a single line. Nothing else changes.

Usage (from the repository root):
  python report/safety_evidence/build_page.py
Writes report/safety_evidence/store/index.html, page.css and page.js.
"""

from __future__ import annotations

import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
META = '<meta name="dash-one-writer">'


def split(source: str) -> dict[str, str]:
    assert source.startswith(META), "the page must open with the one-writer line"
    css = source[source.index("<style>") + len("<style>"):source.index("</style>")]
    js = source[source.index("<script>") + len("<script>"):source.index("</script>")]
    markup = source[source.index("</style>") + len("</style>"):source.index("<script>")]

    css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    css = " ".join(line.strip() for line in css.splitlines() if line.strip())

    lines = []
    for line in js.splitlines():
        line = re.sub(r"\s+//.*$", "", line) if not line.strip().startswith("//") else ""
        if line.strip():
            lines.append(line.strip())
    for line, following in zip(lines, lines[1:] + [""]):
        # joining lines is safe when each one ends a statement, opens or continues one, or the next starts a chain
        assert re.search(r"[;{}(,\[]$|=>$|[|&?:+]$", line) or following.startswith("."), \
            f"line does not end cleanly: {line!r}"
    js = " ".join(lines)

    assert not re.search(r'="[^"]*\'[^"]*"', markup), "an attribute value contains an apostrophe"
    markup = "".join(line.strip() for line in markup.splitlines()).replace('"', "'")
    for text in (css, js, markup):
        assert '"' not in text and "\\" not in text and "\n" not in text
    index = META + "<link rel='stylesheet' href='page.css'>" + markup + "<script src='page.js'></script>"
    return {"index.html": index, "page.css": css, "page.js": js}


def main() -> None:
    out = HERE / "store"
    out.mkdir(exist_ok=True)
    for name, text in split((HERE / "index.html").read_text()).items():
        (out / name).write_text(text)
        print(f"{name}: {len(text)} characters")


if __name__ == "__main__":
    main()
