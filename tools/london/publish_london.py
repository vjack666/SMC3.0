"""Publicación y verificación remota de snapshots ICT 3.0 Londres.

Uso:
  python publish_london.py --repo <root> --folder reports/ict3_london --message "..."
  python publish_london.py --verify-only --sha <commit> --folder reports/ict3_london

El token se lee del Administrador de credenciales de Windows mediante
git-credential-manager get y nunca se imprime ni se escribe en archivos.
"""
import argparse
import base64
import hashlib
import json
import os
import shutil
import subprocess
import sys
import urllib.parse
import urllib.request
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


def gcm_credentials():
    gcm = shutil.which("git-credential-manager.exe") or shutil.which("git-credential-manager")
    if not gcm:
        for candidate in ("/ucrt64/bin/git-credential-manager.exe",
                          "C:/Program Files/Git/mingw64/bin/git-credential-manager.exe"):
            if os.path.isfile(candidate):
                gcm = candidate
                break
    if not gcm:
        raise RuntimeError("git-credential-manager no disponible")
    out = subprocess.run([gcm, "get"], input=b"protocol=https\nhost=github.com\n",
                         capture_output=True).stdout.decode("utf-8", "replace")
    values = {}
    for line in out.splitlines():
        if "=" in line:
            k, v = line.split("=", 1)
            values[k.strip()] = v.strip()
    if not values.get("username") or not values.get("password"):
        raise RuntimeError("credenciales de GitHub no disponibles")
    return values["username"], values["password"]


def push_folder(repo_root, folder, message):
    if isinstance(folder, (list, tuple)):
        return push_paths(repo_root, list(folder), message)
    return push_paths(repo_root, [folder], message)


def push_paths(repo_root, paths, message):
    repo_root = Path(repo_root).resolve()
    for path in paths:
        run(["git", "add", "--", path], cwd=repo_root)
    staged = run(["git", "diff", "--cached", "--name-only"], cwd=repo_root).strip()
    if not staged:
        raise RuntimeError("no hay archivos nuevos para publicar")
    allowed = set()
    for path in paths:
        allowed.add(path)
        allowed.add(path.rstrip("/") + "/")
    if any(not any(line == a or line.startswith(a) for a in allowed)
           for line in staged.splitlines() if line):
        raise RuntimeError("el staged incluye archivos fuera de " + repr(paths))
    run(["git", "commit", "-m", message], cwd=repo_root)
    sha = run(["git", "rev-parse", "HEAD"], cwd=repo_root).strip()
    user, token = gcm_credentials()
    url = "https://{}:{}@github.com/{}.git".format(
        urllib.parse.quote(user, safe=""), urllib.parse.quote(token, safe=""), REPO_SLUG)
    run(["git", "push", url, BRANCH], cwd=repo_root, secret=token)
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
    errors = []
    for entry in manifest.get("files", []):
        rel = folder + "/" + entry["path"]
        remote = remote_bytes(rel, sha)
        local = (root / rel).read_bytes().replace(b"\r\n", b"\n")
        digest = hashlib.sha256(remote.replace(b"\r\n", b"\n")).hexdigest()
        if digest != entry["sha256"] or len(remote.replace(b"\r\n", b"\n")) != entry["bytes"]:
            errors.append(rel)
    readme = remote_bytes(folder + "/snapshot_global.md", sha)
    if b"ICT" not in readme:
        errors.append(folder + "/snapshot_global.md")
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
