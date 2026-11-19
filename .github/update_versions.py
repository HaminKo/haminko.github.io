"""Set each released project's version from its newest GitHub release.

Usage: python update_versions.py FILE [FILE ...]

Finds two patterns:
- index.html: a card <a class="project" href="https://github.com/OWNER/REPO">
  with <span class="status">Released X.Y</span> inside it.
- README.md: a link [Name X.Y](https://github.com/OWNER/REPO).

Versions are written major.minor ("0.2" for v0.2.1). A repo without a
release (or that can't be read) is left as it is. Only the standard library.
"""

import json
import os
import re
import sys
import urllib.error
import urllib.request

CARD = re.compile(
    r'(<a class="project" href="https://github\.com/([\w.-]+/[\w.-]+)">'
    r'(?:(?!</a>).)*?<span class="status">Released )(\d+\.\d+)(</span>)',
    re.S,
)
LINK = re.compile(r"(\[[^\]]*? )(\d+\.\d+)(\]\(https://github\.com/([\w.-]+/[\w.-]+)\))")
TAG = re.compile(r"v?(\d+)\.(\d+)")

_cache: dict[str, str | None] = {}


def latest(repo: str) -> str | None:
    """major.minor of the repo's newest release, or None."""
    if repo not in _cache:
        req = urllib.request.Request(
            f"https://api.github.com/repos/{repo}/releases/latest",
            headers={"Accept": "application/vnd.github+json"},
        )
        token = os.environ.get("GITHUB_TOKEN")
        if token:
            req.add_header("Authorization", f"Bearer {token}")
        try:
            with urllib.request.urlopen(req, timeout=20) as r:
                tag = json.load(r)["tag_name"]
            m = TAG.match(tag)
            _cache[repo] = f"{m[1]}.{m[2]}" if m else None
        except (urllib.error.URLError, KeyError, ValueError) as e:
            print(f"{repo}: no release read ({e})")
            _cache[repo] = None
    return _cache[repo]


def update(text: str) -> str:
    def card(m: re.Match) -> str:
        v = latest(m[2]) or m[3]
        return f"{m[1]}{v}{m[4]}"

    def link(m: re.Match) -> str:
        v = latest(m[4]) or m[2]
        return f"{m[1]}{v}{m[3]}"

    return LINK.sub(link, CARD.sub(card, text))


def main() -> None:
    for path in sys.argv[1:]:
        with open(path, encoding="utf-8") as f:
            old = f.read()
        new = update(old)
        if new != old:
            with open(path, "w", encoding="utf-8", newline="") as f:
                f.write(new)
            print(f"{path}: updated")
        else:
            print(f"{path}: already current")


if __name__ == "__main__":
    main()
