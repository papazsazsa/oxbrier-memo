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
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MEMO_MD = ROOT.parent / "01 Opportunity Memo.md"
INDEX_HTML = ROOT / "index.html"


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
    return markdown.strip() + "\n"


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
        output.append(f'<{tag} class="{klass}" id="{section_id}">\n{heading_html}\n{body}\n</{tag}>')
        first_content_section = False

    body_html = "\n\n".join(output)

    # Pandoc's footnotes section is already in the rendered body after the last h1 split.
    footnotes = re.search(r'(<section class="block sources" id="sources">.*?</section>)', rendered, flags=re.S)
    if footnotes and footnotes.group(1) not in body_html:
        footnote_html = footnotes.group(1)
        footnote_html = footnote_html.replace('<p class="reveal">', '<p>')
        footnote_html = re.sub(r"\s*<hr />\s*", "\n", footnote_html)
        body_html += "\n\n<hr class=\"sep\">\n\n" + footnote_html

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
