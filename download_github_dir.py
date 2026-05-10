#!/usr/bin/env python3
import os, re, json, argparse, urllib.request, urllib.error
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

API = "https://api.github.com"

def _headers():
    h = {"Accept": "application/vnd.github+json", "User-Agent": "gh_download"}
    if tok := os.environ.get("GITHUB_TOKEN"):
        h["Authorization"] = f"Bearer {tok}"
    return h

def _get(url):
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=_headers())) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")
        raise SystemExit(f"API error {e.code}: {json.loads(body).get('message', body)}")

def parse_url(url):
    url = url.rstrip("/")
    if m := re.match(r"https?://github\.com/([^/]+)/([^/]+)/tree/([^/]+)(?:/(.*))?$", url):
        o, r, b, p = m.groups(); return o, r, b, p or ""
    if m := re.match(r"https?://github\.com/([^/]+)/([^/]+)$", url):
        o, r = m.groups(); return o, r, "", ""
    raise SystemExit(f"Unrecognised GitHub URL: {url}")

def download(args):
    url, dest = args
    dest.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(urllib.request.Request(url, headers=_headers())) as r:
        dest.write_bytes(r.read())
    return dest

def main():
    p = argparse.ArgumentParser()
    p.add_argument("url")
    p.add_argument("destination", nargs="?", default=None)
    g = p.add_mutually_exclusive_group()
    g.add_argument("--shallow", action="store_true")
    g.add_argument("--depth", type=int, metavar="N")
    args = p.parse_args()

    max_depth = 1 if args.shallow else args.depth
    owner, repo, branch, remote = parse_url(args.url)

    if not branch:
        branch = _get(f"{API}/repos/{owner}/{repo}")["default_branch"]

    sha = _get(f"{API}/repos/{owner}/{repo}/commits?sha={branch}&per_page=1")[0]["commit"]["tree"]["sha"]
    tree = _get(f"{API}/repos/{owner}/{repo}/git/trees/{sha}?recursive=1")

    if tree.get("truncated"):
        print("⚠️  Tree truncated by GitHub — large repos may be incomplete")

    prefix = remote + "/" if remote else ""
    dest_root = Path(args.destination or Path.cwd()) / (Path(remote).name or repo)

    def within_depth(path):
        if not max_depth:
            return True
        rel = path.removeprefix(prefix)
        return rel.count("/") < max_depth

    raw_url = f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/"
    files = [
        (raw_url + item["path"], dest_root / item["path"].removeprefix(prefix))
        for item in tree["tree"]
        if item["type"] == "blob"
        and item["path"].startswith(prefix)
        and within_depth(item["path"])
        and not (dest_root / item["path"].removeprefix(prefix)).exists()
    ]

    print(f"📂 {owner}/{repo}@{branch}/{remote or ''} → {dest_root.resolve()}")
    print(f"   {len(files)} file(s) to download\n")

    done = 0
    with ThreadPoolExecutor() as ex:
        futures = {ex.submit(download, f): f[1] for f in files}
        for fut in as_completed(futures):
            fut.result()
            done += 1
            print(f"  ↓  [{done}/{len(files)}] {futures[fut]}")

    print(f"\n✅ {done} file(s) → {dest_root.resolve()}")

if __name__ == "__main__":
    main()
