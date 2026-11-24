"""Publicación y verificación remota de snapshots ICT 3.0 Londres.

Uso:
  python publish_london.py --repo <root> --folder reports/ict3_london --message "..."
  python publish_london.py --verify-only --sha <commit> --folder reports/ict3_london

Git usa el administrador de credenciales configurado; no se leen ni se imprimen tokens.
"""
import argparse
import hashlib
import json
import os
import subprocess
import sys
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

REPO_SLUG = "vjack666/SMC3.0"
BRANCH = "main"
API = "https://api.github.com"


def run(cmd, *, cwd=None, input_bytes=None, env=None, secret=None):
    proc = subprocess.run(cmd, cwd=cwd, input=input_bytes, capture_output=True, env=env)
    out = proc.stdout.decode("utf-8", "replace")
    err = proc.stderr.decode("utf-8", "replace")
    if secret:
        out, err = out.replace(secret, "<token>"), err.replace(secret, "<token>")
    if proc.returncode:
        raise RuntimeError((err or out).strip()[:800])
    return out


def push_folder(repo_root, folder, message):
    if isinstance(folder, (list, tuple)):
        return push_paths(repo_root, list(folder), message)
    return push_paths(repo_root, [folder], message)


def push_paths(repo_root, paths, message):
    repo_root = Path(repo_root).resolve()
    target = f"https://github.com/{REPO_SLUG}.git"
    allowed = tuple(p.rstrip("/") for p in paths)
    def check_staged():
        staged = run(["git", "diff", "--cached", "--name-only", "-z"], cwd=repo_root)
        if any(not any(line == p or line.startswith(p + "/") for p in allowed)
               for line in staged.split("\0") if line):
            raise RuntimeError("el staged incluye archivos fuera de " + repr(paths))
        return bool(staged)
    check_staged()
    head = run(["git", "rev-parse", "HEAD"], cwd=repo_root).strip()
    remote = run(["git", "ls-remote", "--exit-code", target, "refs/heads/" + BRANCH],
                 cwd=repo_root).split()[0]
    if head != remote:
        raise RuntimeError("HEAD local no coincide con main remoto; no se publican commits ajenos")
    for path in paths:
        run(["git", "add", "--", path], cwd=repo_root)
    if not check_staged():
        raise RuntimeError("no hay archivos nuevos para publicar")
    run(["git", "commit", "-m", message], cwd=repo_root)
    sha = run(["git", "rev-parse", "HEAD"], cwd=repo_root).strip()
    env = dict(os.environ, GIT_TERMINAL_PROMPT="0", GCM_INTERACTIVE="Never")
    run(["git", "push", target, f"{sha}:refs/heads/{BRANCH}"], cwd=repo_root, env=env)
    return sha


def api_get(path):
    req = urllib.request.Request(API + path, headers={
        "Accept": "application/vnd.github+json",
        "User-Agent": "ict3-london-publisher"})
    with urllib.request.urlopen(req, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def remote_bytes(path, sha):
    # raw.githubusercontent.com pinned to an immutable commit SHA: public read,
    # no GitHub API rate limit, and no stale `main` CDN cache.
    quoted = urllib.parse.quote(path, safe="/")
    url = f"https://raw.githubusercontent.com/{REPO_SLUG}/{sha}/{quoted}"
    req = urllib.request.Request(url, headers={"User-Agent": "ict3-london-publisher"})
    with urllib.request.urlopen(req, timeout=30) as response:
        return response.read()


def verify(repo_root, folder, sha):
    root = Path(repo_root).resolve()
    manifest_path = root / folder / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    entries = manifest.get("files", [])
    errors = []
    if json.loads(remote_bytes(folder + "/manifest.json", sha)) != manifest:
        errors.append(folder + "/manifest.json")

    def verify_entry(entry):
        rel = folder + "/" + entry["path"]
        raw = remote_bytes(rel, sha).replace(b"\r\n", b"\n").replace(b"\r", b"\n")
        if (hashlib.sha256(raw).hexdigest() != entry["sha256"] or len(raw) != entry["bytes"]
                or (entry["path"] == "snapshot_global.md" and b"ICT" not in raw)):
            return rel
        return None

    with ThreadPoolExecutor(max_workers=8) as pool:
        errors.extend(rel for rel in pool.map(verify_entry, entries) if rel)
    return {
        "ok": not errors, "sha": sha, "files_checked": len(manifest.get("files", [])),
        "errors": errors,
        "raw_readme": f"https://raw.githubusercontent.com/{REPO_SLUG}/{sha}/{folder}/snapshot_global.md",
        "raw_manifest": f"https://raw.githubusercontent.com/{REPO_SLUG}/{sha}/{folder}/manifest.json",
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--repo", default=".", help="repo root")
    parser.add_argument("--folder", default="reports/ict3_london", help="folder to publish/verify")
    parser.add_argument("--message", default="docs(ict3): publica snapshot Londres +15m")
    parser.add_argument("--verify-only", action="store_true")
    parser.add_argument("--sha", default=None, help="commit SHA to verify")
    args = parser.parse_args(argv)
    sha = args.sha or run(["git", "rev-parse", "HEAD"], cwd=args.repo).strip()
    if not args.verify_only:
        sha = push_folder(args.repo, args.folder, args.message)
    result = verify(args.repo, args.folder, sha)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["ok"] else 2


if __name__ == "__main__":
    sys.exit(main())
