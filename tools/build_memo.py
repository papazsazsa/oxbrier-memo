#!/usr/bin/env python3
"""
Build the public Oxbrier memo site from the canonical markdown memo.

Source of truth:
  ../01 Opportunity Memo.md

Output:
  ./index.html
"""

from __future__ import annotations

import html
import re
import subprocess
import sys
import tempfile
from urllib.parse import urlparse
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MEMO_MD = ROOT.parent / "01 Opportunity Memo.md"
INDEX_HTML = ROOT / "index.html"
ORDERED_NOTES: list[tuple[str, str]] = []


def run_pandoc(markdown: str) -> str:
    with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False) as tmp:
        tmp.write(markdown)
        tmp_path = Path(tmp.name)

    try:
        return subprocess.check_output(
            [
                "pandoc",
                str(tmp_path),
                "--from=gfm+footnotes-tex_math_dollars",
                "--to=html",
            ],
            text=True,
            stderr=subprocess.PIPE,
        )
    except FileNotFoundError:
        raise SystemExit("pandoc is required. Install pandoc or run this from the Codex workspace.")
    except subprocess.CalledProcessError as exc:
        sys.stderr.write(exc.stderr)
        raise SystemExit(exc.returncode)
    finally:
        tmp_path.unlink(missing_ok=True)


def prepare_markdown(markdown: str) -> str:
    markdown = re.sub(r"%%.*?%%\s*", "", markdown, flags=re.S)
    markdown = markdown.replace("==", "")
    markdown = normalize_footnotes(markdown)
    return markdown.strip() + "\n"


def normalize_footnotes(markdown: str) -> str:
    global ORDERED_NOTES
    defs: dict[str, str] = {}
    body_lines: list[str] = []
    current_label: str | None = None
    current_lines: list[str] = []

    def flush_def() -> None:
        nonlocal current_label, current_lines
        if current_label is not None:
            defs[current_label] = "\n".join(current_lines).rstrip()
        current_label = None
        current_lines = []

    for line in markdown.splitlines():
        match = re.match(r"^\[\^([^\]]+)\]:\s*(.*)$", line)
        if match:
            flush_def()
            current_label = match.group(1)
            current_lines = [match.group(2)]
            continue
        if current_label is not None:
            if line.startswith(" ") or line.startswith("\t") or not line.strip():
                current_lines.append(line)
                continue
            flush_def()
        body_lines.append(line)
    flush_def()

    body = "\n".join(body_lines)
    order: list[str] = []

    def replace_ref(match: re.Match[str]) -> str:
        label = match.group(1)
        if label not in defs:
            return match.group(0)
        if label not in order:
            order.append(label)
        n = order.index(label) + 1
        return f'<sup class="fn"><a data-fn="{n}" href="#fn-{n}">{n}</a></sup>'

    body = re.sub(r"\[\^([^\]]+)\]", replace_ref, body)
    ORDERED_NOTES = [(label, defs[label]) for label in order]
    return body.rstrip() + "\n"


def title_case_heading(text: str) -> str:
    small = {"a", "an", "and", "as", "at", "but", "by", "for", "in", "of", "on", "or", "the", "to", "vs", "with"}
    words = re.split(r"(\s+)", text.strip().lower())
    titled: list[str] = []
    word_index = 0
    word_count = len([w for w in words if w.strip()])
    for word in words:
        if not word.strip():
            titled.append(word)
            continue
        bare = re.sub(r"[^a-z0-9&/-]", "", word)
        if word_index not in {0, word_count - 1} and bare in small:
            titled.append(word)
        elif bare == "a24":
            titled.append(word.replace("a24", "A24"))
        elif bare == "d2c":
            titled.append(word.replace("d2c", "D2C"))
        else:
            titled.append(word[:1].upper() + word[1:])
        word_index += 1
    return "".join(titled)


def transform_footnotes(rendered: str) -> str:
    rendered = re.sub(
        r'<a\s+href="#fn(\d+)"[^>]*class="footnote-ref"[^>]*>\s*<sup>(\d+)</sup>\s*</a>',
        r'<sup class="fn"><a data-fn="\1" href="#fn-\1">\2</a></sup>',
        rendered,
        flags=re.S,
    )
    rendered = re.sub(r'id="fn(\d+)"', r'id="fn-\1"', rendered)
    rendered = re.sub(r"\s*<a\s+href=\"#fnref\d+\"[^>]*class=\"footnote-back\"[^>]*>.*?</a>", "", rendered, flags=re.S)
    rendered = re.sub(
        r'<section\s+id="footnotes"[^>]*class="footnotes footnotes-end-of-document"[^>]*>\s*<hr />\s*',
        '<section class="block sources" id="sources">\n<div class="section-title reveal">Sources</div>\n',
        rendered,
        flags=re.S,
    )
    return rendered


def add_reveal_classes(fragment: str, hero: bool = False) -> str:
    p_class = ' class="lede reveal"' if hero else ' class="reveal"'
    fragment = re.sub(r"<p>", f"<p{p_class}>", fragment)
    fragment = re.sub(r"<blockquote>", '<blockquote class="pull reveal">', fragment)
    fragment = re.sub(r"<table>", '<div class="tbl-wrap tbl-wide reveal">\n<table>', fragment)
    fragment = re.sub(r"</table>", "</table>\n</div>", fragment)
    fragment = re.sub(
        r'<a\s+href="mailto:chris@oxbrier\.com">\s*(?:<span>)?chris@oxbrier\.com(?:</span>)?\s*</a>',
        '<a href="mailto:chris&#64;oxbrier&#46;com">chris&#64;oxbrier&#46;com</a>',
        fragment,
        flags=re.S,
    )
    return fragment


def tighten_key_takeaways(fragment: str) -> str:
    fragment = fragment.replace('<div class="tbl-wrap tbl-wide reveal">\n<table>', '<div class="tbl-wrap reveal">\n<table class="tbl-takeaways">', 1)

    def repl_li(match: re.Match[str]) -> str:
        raw = match.group(1).strip()
        raw = re.sub(r"<strong>(.*?)</strong>\s*[–-]\s*", r'<span class="kt-label">\1.</span> ', raw, count=1)
        return f'<p class="reveal">{raw}</p>'

    fragment = re.sub(r"<ul>\s*(.*?)\s*</ul>", lambda m: re.sub(r"<li>(.*?)</li>", repl_li, m.group(1), flags=re.S), fragment, count=1, flags=re.S)
    fragment = fragment.replace(
        '<p class="reveal">Chris Papasadero <a href="mailto:chris&#64;oxbrier&#46;com">chris&#64;oxbrier&#46;com</a></p>',
        '<p class="reveal contact-lede">Chris Papasadero<br><a href="mailto:chris&#64;oxbrier&#46;com">chris&#64;oxbrier&#46;com</a></p>',
    )
    return fragment


def classify_section_tables(section_id: str, fragment: str) -> str:
    table_classes = {
        "we-own-the-supply": "tbl-films",
        "we-cultivate-demand": "tbl-editorial",
    }
    table_class = table_classes.get(section_id)
    if table_class is None:
        return fragment
    return fragment.replace("<table>", f'<table class="{table_class}">', 1)


def clean_sources(source_html: str) -> str:
    source_html = source_html.replace("<p>", "<span>").replace("</p>", "</span>")
    source_html = re.sub(r'<a href="(https?://[^"]+)">https?://[^<]+</a>', r'<a href="\1" target="_blank" rel="noopener">\1</a>', source_html)
    return source_html


def render_note(markdown: str) -> str:
    html_text = run_pandoc(markdown.strip())
    html_text = re.sub(r"^\s*<p>|</p>\s*$", "", html_text.strip(), flags=re.S)

    def label_url(match: re.Match[str]) -> str:
        url = match.group(1)
        text = re.sub(r"\s+", "", match.group(2))
        if text != url:
            return match.group(0)
        host = urlparse(url).netloc.replace("www.", "")
        return f'<a href="{html.escape(url)}" target="_blank" rel="noopener">{html.escape(host or "source")}</a>'

    html_text = re.sub(r'<a\s+href="(https?://[^"]+)">\s*(https?://.*?)\s*</a>', label_url, html_text, flags=re.S)
    return html_text


def render_sources() -> str:
    items = []
    for i, (_label, note) in enumerate(ORDERED_NOTES, start=1):
        items.append(f'<li id="fn-{i}"><span>{render_note(note)}</span></li>')
    return '<section class="block sources" id="sources">\n<div class="section-title reveal">Sources</div>\n<ol>\n' + "\n".join(items) + "\n</ol>\n</section>"


def insert_media(section_id: str, fragment: str) -> str:
    if section_id == "we-own-the-supply":
        fragment = re.sub(
            r"(<p class=\"reveal\">British SAS trained the cast for months;.*?</p>)",
            r'\1\n\n<figure class="reveal media"><img src="assets/magchange.gif" alt="Val Kilmer mag change in Heat" loading="lazy"></figure>',
            fragment,
            count=1,
            flags=re.S,
        )
    if section_id == "we-cultivate-demand":
        fragment = re.sub(
            r"(<p class=\"reveal\">Oxbrier cultivates demand.*?</p>)",
            r'\1\n\n<figure class="reveal media"><img src="assets/gtsmile.gif" alt="" loading="lazy"></figure>',
            fragment,
            count=1,
            flags=re.S,
        )
    return fragment


def render_sections(rendered: str) -> str:
    rendered = transform_footnotes(rendered)
    rendered = re.sub(r"<h1 id=\"sources\">Sources</h1>\s*", "", rendered, flags=re.I)
    rendered = re.sub(r"^\s*<hr />\s*", "", rendered)

    # Split top-level markdown sections while keeping the h1 blocks.
    parts = re.split(r'(<h1 id="([^"]+)">(.+?)</h1>)', rendered, flags=re.S)
    output: list[str] = []
    preamble = parts[0].strip()
    if preamble:
        output.append(add_reveal_classes(preamble))

    first_content_section = True
    for i in range(1, len(parts), 4):
        full_h1 = parts[i]
        section_id = parts[i + 1]
        heading = re.sub(r"<.*?>", "", parts[i + 2])
        body = parts[i + 3].strip()
        body = re.sub(r'<section class="block sources" id="sources">.*?</section>\s*', "", body, flags=re.S)
        body = re.sub(r"\s*<hr />\s*$", "", body)

        if section_id == "sources":
            continue

        if section_id == "footnotes":
            output.append(body)
            continue

        heading_html = f'<div class="section-title reveal">{html.escape(title_case_heading(heading))}</div>'
        body = add_reveal_classes(body, hero=first_content_section)
        body = insert_media(section_id, body)
        tag = "header" if first_content_section else "section"
        klass = "hero" if first_content_section else "block"
        if section_id == "key-takeaways":
            klass += " section-band"
            body = tighten_key_takeaways(body)
        else:
            body = classify_section_tables(section_id, body)
        output.append(f'<{tag} class="{klass}" id="{section_id}">\n{heading_html}\n{body}\n</{tag}>')
        first_content_section = False

    body_html = "\n\n".join(output)

    body_html += "\n\n<hr class=\"sep\">\n\n" + render_sources()

    return body_html


def patch_template(body_html: str) -> str:
    template = INDEX_HTML.read_text()
    start = template.index("<main>") + len("<main>")
    end = template.index("</main>")
    legal = '\n\n  <p class="legal-notice">All contents proprietary and confidential&nbsp;·&nbsp;Oxbrier LLC 2026</p>\n\n'
    return template[:start] + "\n\n" + body_html + legal + template[end:]


def main() -> None:
    markdown = prepare_markdown(MEMO_MD.read_text())
    rendered = run_pandoc(markdown)
    body_html = render_sections(rendered)
    INDEX_HTML.write_text(patch_template(body_html))
    print(f"Built {INDEX_HTML.relative_to(ROOT)} from {MEMO_MD.relative_to(ROOT.parent)}")


if __name__ == "__main__":
    main()
