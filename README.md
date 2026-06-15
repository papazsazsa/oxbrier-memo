# Oxbrier Memo Site

This folder is the GitHub Pages repo for `memo.oxbrier.com`.

Canonical content lives one level up:

```text
../01 Opportunity Memo.md
```

Do not hand-edit memo copy in `index.html`. Edit the markdown, then publish:

```bash
tools/publish_memo.sh "Update opportunity memo"
```

That command rebuilds `index.html`, commits it, and pushes to GitHub Pages.

To rebuild without publishing:

```bash
python3 tools/build_memo.py
```

GitHub Pages serves the repo root. `CNAME` points the site at `memo.oxbrier.com`.
