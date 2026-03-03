#!/usr/bin/env python3
import json
import re
from html.parser import HTMLParser
from pathlib import Path
from typing import List, Optional

ROOT = Path(__file__).resolve().parent
INDEX_HTML = ROOT / "index.html"
OUT_JSON = ROOT / "search-index.json"


class TextExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self._skip_depth = 0
        self.parts = []

    def handle_starttag(self, tag, attrs):
        if tag in {"script", "style"}:
            self._skip_depth += 1

    def handle_endtag(self, tag):
        if tag in {"script", "style"} and self._skip_depth > 0:
            self._skip_depth -= 1

    def handle_data(self, data):
        if self._skip_depth == 0:
            txt = data.strip()
            if txt:
                self.parts.append(txt)


def extract_text(html: str) -> str:
    parser = TextExtractor()
    parser.feed(html)
    text = " ".join(parser.parts)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def extract_title(html: str, fallback: str) -> str:
    m = re.search(r"<title>(.*?)</title>", html, flags=re.IGNORECASE | re.DOTALL)
    if m:
        return re.sub(r"\s+", " ", m.group(1)).strip()
    m = re.search(r"<h1[^>]*>(.*?)</h1>", html, flags=re.IGNORECASE | re.DOTALL)
    if m:
        plain = re.sub(r"<[^>]+>", " ", m.group(1))
        return re.sub(r"\s+", " ", plain).strip()
    return fallback


def find_source_for_href(href: str, all_html: List[Path]) -> Optional[Path]:
    p = ROOT / href
    if p.exists() and p.is_file():
        return p

    by_name = [x for x in all_html if x.name == Path(href).name]
    if len(by_name) == 1:
        return by_name[0]
    return None


def main():
    if not INDEX_HTML.exists():
        raise SystemExit("index.html not found")

    index_html = INDEX_HTML.read_text(encoding="utf-8")
    hrefs = re.findall(r'<a\s+href="([^"]+\.html)"', index_html, flags=re.IGNORECASE)
    seen = set()
    ordered_hrefs = []
    for h in hrefs:
        if h not in seen:
            seen.add(h)
            ordered_hrefs.append(h)

    all_html = [p for p in ROOT.rglob("*.html") if p.name != "index.html"]
    rows = []
    for href in ordered_hrefs:
        src = find_source_for_href(href, all_html)
        if src and src.exists():
            html = src.read_text(encoding="utf-8", errors="ignore")
            title = extract_title(html, Path(href).stem)
            content = extract_text(html)
            rows.append({
                "href": href,
                "source": str(src.relative_to(ROOT)).replace("\\", "/"),
                "title": title,
                "content": content,
            })
        else:
            rows.append({
                "href": href,
                "source": None,
                "title": Path(href).stem,
                "content": "",
            })

    OUT_JSON.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {OUT_JSON} with {len(rows)} entries")


if __name__ == "__main__":
    main()
