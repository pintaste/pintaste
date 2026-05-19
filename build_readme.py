import re
import pathlib
import requests
import os

root = pathlib.Path(__file__).parent.resolve()
TOKEN = os.environ.get("GH_TOKEN", "")
GITHUB_USER = "pintaste"
MAX_RELEASES = 6


def replace_chunk(content, marker, chunk, inline=False):
    r = re.compile(
        r"<!\-\- {} starts \-\->.*<!\-\- {} ends \-\->".format(marker, marker),
        re.DOTALL,
    )
    if not inline:
        chunk = "\n{}\n".format(chunk)
    chunk = "<!-- {} starts -->{}<!-- {} ends -->".format(marker, chunk, marker)
    return r.sub(chunk, content)


def gh_get(path):
    headers = {"Accept": "application/vnd.github+json"}
    if TOKEN:
        headers["Authorization"] = f"Bearer {TOKEN}"
    resp = requests.get(f"https://api.github.com{path}", headers=headers)
    return resp.json() if resp.ok else None


def fetch_releases():
    repos = gh_get(f"/users/{GITHUB_USER}/repos?type=owner&per_page=100") or []
    releases = []
    for repo in repos:
        if repo.get("fork") or repo.get("private") or repo.get("archived"):
            continue
        name = repo["name"]
        repo_releases = gh_get(f"/repos/{GITHUB_USER}/{name}/releases?per_page=5") or []
        for release in repo_releases:
            if release.get("prerelease") or release.get("draft"):
                continue
            releases.append({
                "repo": name,
                "tag": release["tag_name"],
                "url": release["html_url"],
                "date": release["published_at"][:10],
            })

    releases.sort(key=lambda r: r["date"], reverse=True)

    # One latest release per repo
    seen = set()
    unique = []
    for r in releases:
        if r["repo"] not in seen:
            seen.add(r["repo"])
            unique.append(r)

    return unique[:MAX_RELEASES]


def fetch_stats():
    user = gh_get(f"/users/{GITHUB_USER}") or {}
    return {"followers": user.get("followers", 0)}


if __name__ == "__main__":
    readme = root / "README.md"
    content = readme.read_text()

    releases = fetch_releases()
    releases_md = "<br>".join(
        f"• [{r['repo']} {r['tag']}]({r['url']}) - {r['date']}"
        for r in releases
    ) or "• No releases yet"
    content = replace_chunk(content, "recent_releases", releases_md)

    stats = fetch_stats()
    stats_text = f"{stats['followers']:,} followers"
    content = replace_chunk(content, "github_stats", stats_text, inline=True)

    readme.write_text(content)
    print("README updated.")
    print(content)
