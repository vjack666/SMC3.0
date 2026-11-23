"""INVARIANT 4: deterministic, idempotent bundle writer."""

from helpers import make_bundle, sandbox_dir, sha256, write_bundle


def test_two_writes_produce_identical_bytes_and_hashes():
    bundle = make_bundle()
    with sandbox_dir() as root:
        first = write_bundle(bundle, root)
        snapshot = {p: (root / p).read_bytes() for p in first["hashes"]}
        second = write_bundle(bundle, root)
        assert first["bundle_sha256"] == second["bundle_sha256"]
        assert first["hashes"] == second["hashes"]
        for path, digest in first["hashes"].items():
            assert sha256((root / path).read_bytes()) == digest
            assert (root / path).read_bytes() == snapshot[path]


def test_second_write_reports_no_changes_and_no_duplicate_files():
    bundle = make_bundle()
    with sandbox_dir() as root:
        first = write_bundle(bundle, root)
        before = sorted(str(p.relative_to(root)).replace("\\", "/")
                        for p in root.rglob("*") if p.is_file())
        second = write_bundle(bundle, root)
        after = sorted(str(p.relative_to(root)).replace("\\", "/")
                       for p in root.rglob("*") if p.is_file())
        assert first["changed"]
        assert second["changed"] == []
        assert before == after
        assert len(before) == first["file_count"] == second["file_count"]


def test_content_change_changes_bundle_hash():
    bundle = make_bundle()
    with sandbox_dir() as root:
        base = write_bundle(bundle, root)
    changed = make_bundle()
    changed["instruments"]["EURUSD"]["pois"][0]["state"] = "MITIGATED"
    with sandbox_dir() as root:
        modified = write_bundle(changed, root)
    assert modified["bundle_sha256"] != base["bundle_sha256"]
