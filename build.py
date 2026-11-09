#!/usr/bin/env python3
"""Render writing/*.md to styled HTML and refresh the index's Writing list.

    pip install markdown
    python build.py

Each post starts with a two-line header:

    title: Passing 19/19 injection tests
    date: 2026-07-14

...followed by a blank line, then normal Markdown.
"""
import html
import json
import pathlib
import re
import subprocess

import markdown

ROOT = pathlib.Path(__file__).parent
WRITING = ROOT / "writing"

# Work account; its private counts are public on its profile, so the viewer token can read them.
WORK_LOGIN = "anshul-qc"

CONTRIB_QUERY = """
fragment cal on ContributionsCollection {
  contributionCalendar {
    weeks { contributionDays { contributionCount date } }
  }
}
query {
  viewer { contributionsCollection { ...cal } }
  work: user(login: "%s") { contributionsCollection { ...cal } }
}
""" % WORK_LOGIN

POST = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title} &mdash; anshul srivastava</title>
<link rel="stylesheet" href="../style.css">
<link rel="icon" href="data:,">
</head>
<body>
<nav class="post-nav"><a href="../index.html">&larr; anshul srivastava</a></nav>
<article>
<header>
<h1>{title}</h1>
<p class="date">{date}</p>
</header>
{body}
</article>
</body>
</html>
"""


def parse(path):
    """Split the `key: value` header from the Markdown body."""
    meta, _, body = path.read_text().partition("\n\n")
    fields = dict(
        re.match(r"(\w+):\s*(.*)", line).groups()
        for line in meta.strip().splitlines()
    )
    return fields["title"], fields["date"], body


def contributions():
    """Render the contribution calendar via the authenticated `gh` CLI.

    Uses `viewer`, not `user(login:)`, so private-repo contributions are counted —
    which is the whole point: the public scrapers miss them.
    Returns None if gh is unavailable, so a failed fetch leaves the last grid in place.
    """
    try:
        out = subprocess.run(
            ["gh", "api", "graphql", "-f", f"query={CONTRIB_QUERY}"],
            capture_output=True, text=True, check=True,
        ).stdout
    except (OSError, subprocess.CalledProcessError) as e:
        print(f"  ! skipping commit graph: {e}")
        return None

    data = json.loads(out)["data"]
    viewer, work = (
        data[k]["contributionsCollection"]["contributionCalendar"]["weeks"] for k in ("viewer", "work")
    )

    # Sum both accounts per day; the viewer's weeks set the grid.
    counts = {}
    for weeks in (viewer, work):
        for week in weeks:
            for d in week["contributionDays"]:
                counts[d["date"]] = counts.get(d["date"], 0) + d["contributionCount"]

    # GitHub's levels are per account, so recompute them from quartiles of the combined non-zero days.
    nonzero = sorted(c for c in counts.values() if c)
    cuts = [nonzero[len(nonzero) * k // 4] for k in (1, 2, 3)] if nonzero else []

    def level(c):
        return 1 + sum(c > t for t in cuts) if c else 0

    weeks = []
    for week in viewer:
        days = "".join(
            f'<i class="l{level(counts[d["date"]])}" title="{counts[d["date"]]} on {d["date"]}"></i>'
            for d in week["contributionDays"]
        )
        weeks.append(f'<div class="wk">{days}</div>')

    return f'<div class="cal">{"".join(weeks)}</div>'


def splice(text, marker, body):
    """Replace the content between <!-- marker:start --> and <!-- marker:end -->."""
    return re.sub(
        rf"(<!-- {marker}:start -->).*?(<!-- {marker}:end -->)",
        lambda m: m.group(1) + "\n    " + body + "\n    " + m.group(2),
        text,
        flags=re.S,
    )


def main():
    posts = []
    for md in sorted(WRITING.glob("*.md")):
        title, date, body = parse(md)
        out = md.with_suffix(".html")
        out.write_text(POST.format(
            title=html.escape(title),
            date=date,
            body=markdown.markdown(body, extensions=["fenced_code", "tables"]),
        ))
        posts.append((date, title, out.name))
        print(f"  {md.name} -> writing/{out.name}")

    posts.sort(reverse=True)  # newest first

    # No posts yet -> hide the whole Writing section rather than showing an empty one.
    if posts:
        lines = "\n      ".join(
            '<div class="branch">'
            f'<span class="glyph">{"└──" if i == len(posts) - 1 else "├──"}</span>'
            f'<span class="date">{date}</span>'
            f'<span><a href="writing/{name}">{html.escape(title)}</a></span>'
            "</div>"
            for i, (date, title, name) in enumerate(posts)
        )
        section = (
            '<section>\n    <h2>Writing</h2>\n'
            f'    <div class="tree posts">\n      {lines}\n    </div>\n  </section>'
        )
    else:
        section = ""

    index = ROOT / "index.html"
    text = splice(index.read_text(), "writing", section)
    print(f"  index.html -> {len(posts)} post(s) listed")

    grid = contributions()
    if grid:
        text = splice(text, "commits", grid)
        print("  index.html -> commit graph refreshed")

    index.write_text(text)


if __name__ == "__main__":
    main()
