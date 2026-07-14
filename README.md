# anshxl.github.io

Personal site. Static HTML/CSS, no framework.

## Writing

Drop a Markdown file in `writing/` with a two-line header:

```
title: Post title
date: 2026-07-14

Body in Markdown...
```

Then run the build:

```
pip install markdown
python3 build.py
```

`build.py` renders `writing/*.md` to HTML, refreshes the Writing list, and
regenerates the contribution graph from the GitHub GraphQL API via the
authenticated `gh` CLI (so private contributions are counted). Commit the
generated HTML — the site is served as-is, nothing runs on deploy.
