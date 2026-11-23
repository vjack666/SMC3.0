"""INVARIANT 6: manifest SHA-256 computed on LF-normalized bytes."""

import json

from helpers import (
    normalize_lf,
    render_bundle,
    sandbox_dir,
    sha256,
    verify_manifest,
    write_bundle,
    make_bundle,
)


def test_manifest_hash_matches_lf_normalized_bytes():
    bundle = make_bundle()
    with sandbox_dir() as root:
        result = write_bundle(bundle, root)
        manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
        assert verify_manifest(root, manifest) == []
        for entry in manifest["files"]:
            data = (root / entry["path"]).read_bytes()
            assert entry["sha256"] == sha256(normalize_lf(data))
            assert entry["bytes"] == len(normalize_lf(data))
        assert result["hashes"]["manifest.json"] == sha256(
            (root / "manifest.json").read_bytes()
        )


def test_crlf_file_verifies_after_lf_normalization():
    bundle = make_bundle()
    files = render_bundle(bundle)
    from helpers import build_manifest
    manifest = build_manifest(files, bundle)
    with sandbox_dir() as root:
        for path, data in files.items():
            target = root / path
            target.parent.mkdir(parents=True, exist_ok=True)
            # Deliberately store CRLF on disk; manifest was built over LF.
            target.write_bytes(data.replace(b"\n", b"\r\n"))
        assert verify_manifest(root, manifest) == []


def test_raw_crlf_hash_does_not_match_manifest():
    bundle = make_bundle()
    files = render_bundle(bundle)
    from helpers import build_manifest
    manifest = build_manifest(files, bundle)
    entry = next(e for e in manifest["files"] if e["path"] == "snapshot.json")
    raw_crlf = files["snapshot.json"].replace(b"\n", b"\r\n")
    assert sha256(raw_crlf) != entry["sha256"]
    assert sha256(normalize_lf(raw_crlf)) == entry["sha256"]


def test_corrupted_checksum_is_detected():
    bundle = make_bundle()
    with sandbox_dir() as root:
        result = write_bundle(bundle, root)
        manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
        target = root / "data_quality.json"
        target.write_bytes(target.read_bytes().replace(b"PASSED", b"FAILED"))
        errors = verify_manifest(root, manifest)
        assert errors
        assert any("data_quality.json" in e for e in errors)
        assert result["hashes"]["data_quality.json"] != sha256(target.read_bytes())
