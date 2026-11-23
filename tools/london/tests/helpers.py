"""Self-contained synthetic helpers for the P5 London snapshot invariant suite.

Rules enforced here:
  * stdlib only -- no MT5, no network, no imports from any other agent's module;
  * no credentials, no account identity, no local paths in the generated data;
  * every fixture is deterministic (fixed dates, fixed content, sorted output).

The helper functions double as the small "reference implementation" under test:
each invariant is implemented as a pure checker fed by synthetic bundles, and
the pytest modules assert both the happy path and an injected violation.
"""

from __future__ import annotations

import hashlib
import json
import re
from contextlib import contextmanager
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from zoneinfo import ZoneInfo

UTC = timezone.utc
LONDON_TZ = ZoneInfo("Europe/London")
GUAYAQUIL_TZ = ZoneInfo("America/Guayaquil")

CUTOFF_DATE = date(2026, 11, 23)
ENGINE_REVISION = "synthetic-engine-rev-0"
SCHEMA_VERSION = "london-snapshot/v1"
SOURCE_REPOSITORY = "vjack666/SMC3.0"
PROVIDER = "SYNTHETIC-FIXTURE"

FORBIDDEN_TRADING_KEYS = {
    "order", "orders", "trade", "trades", "position", "positions",
    "position_size", "lot", "lots", "stop_loss", "take_profit", "pnl",
    "profit", "equity", "margin", "balance", "action", "execution",
    "executed_order", "buys", "sells",
}
FORBIDDEN_PRIVACY_KEYS = {
    "login", "password", "passwd", "token", "access_token", "refresh_token",
    "api_key", "secret", "account", "account_number", "account_id", "balance",
    "equity", "margin", "pnl", "profit", "username", "user", "email",
    "client_id", "authorization", "cookie", "local_path", "filepath",
    "file_path", "path", "home", "home_dir", "hostname", "ip",
}
MANIFEST_REQUIRED_KEYS = {
    "schema_version", "snapshot_id", "snapshot_cutoff_utc", "generated_at_utc",
    "engine_revision", "mode", "files",
}
PATH_PATTERNS = (
    re.compile(r"[A-Za-z]:[\\/](?:Users|home|tmp|AppData)", re.I),
    re.compile(r"^(?:\\\\|//)[^\\/]+[\\/]", re.I),
    re.compile(r"/(?:home|Users|root)/", re.I),
)


# ---------------------------------------------------------------------------
# Time helpers (offsets are always read from zoneinfo, never hardcoded)
# ---------------------------------------------------------------------------
def london_cutoff(d: date = CUTOFF_DATE) -> datetime:
    """08:15 wall clock in Europe/London, timezone-aware (GMT or BST)."""
    return datetime.combine(d, time(8, 15), tzinfo=LONDON_TZ)


def to_utc(dt: datetime) -> datetime:
    return dt.astimezone(UTC)


def iso_utc(dt: datetime) -> str:
    return to_utc(dt).isoformat().replace("+00:00", "Z")


def parse_iso_utc(value) -> datetime:
    if not isinstance(value, str):
        raise ValueError(f"not an ISO timestamp: {value!r}")
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        raise ValueError(f"timestamp lacks an offset: {value!r}")
    return to_utc(dt)


def london_0815_utc(d: date = CUTOFF_DATE) -> datetime:
    """The single causal cut, converted through the IANA zone."""
    return to_utc(london_cutoff(d))


def london_0815_guayaquil(d: date = CUTOFF_DATE) -> datetime:
    return london_cutoff(d).astimezone(GUAYAQUIL_TZ)


# ---------------------------------------------------------------------------
# Bar helpers: position zero of the requested feed is the discarded anchor
# ---------------------------------------------------------------------------
def make_bar(open_london: datetime, minutes: int = 15) -> dict:
    close_london = open_london + timedelta(minutes=minutes)
    return {
        "tf": "M15",
        "open_london": open_london.isoformat(),
        "close_london": close_london.isoformat(),
        "open_utc": iso_utc(open_london),
        "close_utc": iso_utc(close_london),
    }


def make_raw_feed(d: date = CUTOFF_DATE, *, poison_index0: bool = False) -> list:
    """Four requested M15 bars; index 0 is the anchor `closed_frame` drops."""
    base = datetime.combine(d, time(7, 30), tzinfo=LONDON_TZ)
    bars = [make_bar(base + timedelta(minutes=15 * i)) for i in range(4)]
    if poison_index0:
        # A future bar in position zero: using it would be look-ahead.
        bars[0] = make_bar(datetime.combine(d, time(23, 0), tzinfo=LONDON_TZ))
    return bars


def closed_frame(raw_feed: list) -> list:
    return list(raw_feed[1:])


def latest_closed(raw_feed: list, cutoff_utc: datetime) -> dict | None:
    eligible = [
        b for b in closed_frame(raw_feed)
        if parse_iso_utc(b["close_utc"]) <= cutoff_utc
    ]
    return eligible[-1] if eligible else None


def validate_bar(bar: dict, tf: str = "M15", minutes: int = 15) -> list:
    errors = []
    try:
        opened = parse_iso_utc(bar["open_utc"])
        closed = parse_iso_utc(bar["close_utc"])
    except (KeyError, ValueError) as exc:
        return [f"invalid bar timestamps: {exc}"]
    if bar.get("tf") != tf:
        errors.append(f"wrong tf: {bar.get('tf')!r}")
    if closed <= opened:
        errors.append("close not after open")
    if int((closed - opened).total_seconds() // 60) != minutes:
        errors.append("wrong bar duration")
    return errors


# ---------------------------------------------------------------------------
# Generic key/path scanners
# ---------------------------------------------------------------------------
def find_forbidden_keys(obj, forbidden: set, prefix: str = "") -> list:
    hits = []
    if isinstance(obj, dict):
        for key, value in obj.items():
            path = f"{prefix}.{key}" if prefix else str(key)
            if str(key).lower() in forbidden:
                hits.append(path)
            hits.extend(find_forbidden_keys(value, forbidden, path))
    elif isinstance(obj, (list, tuple)):
        for index, value in enumerate(obj):
            hits.extend(find_forbidden_keys(value, forbidden, f"{prefix}[{index}]"))
    return hits


def find_local_paths(obj, prefix: str = "") -> list:
    hits = []
    if isinstance(obj, dict):
        for key, value in obj.items():
            path = f"{prefix}.{key}" if prefix else str(key)
            hits.extend(find_local_paths(value, path))
    elif isinstance(obj, (list, tuple)):
        for index, value in enumerate(obj):
            hits.extend(find_local_paths(value, f"{prefix}[{index}]"))
    elif isinstance(obj, str):
        for pattern in PATH_PATTERNS:
            if pattern.search(obj):
                hits.append(f"{prefix}={obj!r}")
                break
    return hits


# ---------------------------------------------------------------------------
# Synthetic bundle fixture and invariant checkers
# ---------------------------------------------------------------------------
def make_bundle(
    d: date = CUTOFF_DATE,
    *,
    symbols=("EURUSD", "GBPUSD"),
    mode: str = "OBSERVE_ONLY_NO_ORDER",
) -> dict:
    cutoff_l = london_cutoff(d)
    cutoff_u = to_utc(cutoff_l)
    instruments = {}
    for symbol in symbols:
        raw = make_raw_feed(d)
        last = latest_closed(raw, cutoff_u)
        instruments[symbol] = {
            "events": [{
                "event_id": f"E-{symbol}-001",
                "observed_at": iso_utc(cutoff_u - timedelta(minutes=20)),
                "kind": "CALENDAR_HIGH_IMPACT",
            }],
            "pois": [{
                "poi_id": f"P-{symbol}-001",
                "created_at": iso_utc(cutoff_u - timedelta(hours=3)),
                "origin_tf": "H4",
                "type": "OB",
                "state": "NOT_EXPOSED",
            }],
            "candidates": [{
                "candidate_id": f"C-{symbol}-001",
                "entry_authorized": False,
                "reason": "WAIT_FOR_CONFIRMATION",
            }],
            # Requested feed only; position 0 is discarded before inference.
            "raw_feed": raw,
            "last_bar_open_utc": last["open_utc"],
            "last_bar_close_utc": last["close_utc"],
            "bars_count": len(closed_frame(raw)),
            "oldest_bar_utc": closed_frame(raw)[0]["open_utc"],
            "feed_source": PROVIDER,
            "freshness_status": "FRESH",
        }
    return {
        "schema_version": SCHEMA_VERSION,
        "snapshot_id": f"london-{d.isoformat()}-0815",
        "snapshot_cutoff_london": cutoff_l.isoformat(),
        "snapshot_cutoff_utc": iso_utc(cutoff_u),
        "snapshot_cutoff_guayaquil": london_0815_guayaquil(d).isoformat(),
        "generated_at_utc": iso_utc(cutoff_u + timedelta(minutes=6)),
        "engine_revision": ENGINE_REVISION,
        "source_repository": SOURCE_REPOSITORY,
        "provider": PROVIDER,
        "mode": mode,
        "exported": sorted(instruments),
        "stale": [],
        "unavailable": [],
        "instruments": instruments,
        "validation": {"status": "PASSED", "observe_only": True},
    }


def check_no_lookahead(bundle: dict, cutoff_utc: datetime) -> list:
    """Only event/POI timestamps are market information; export times are not."""
    errors = []
    for symbol, inst in bundle.get("instruments", {}).items():
        for section in ("events", "pois"):
            for index, item in enumerate(inst.get(section, [])):
                for key, value in item.items():
                    if key.endswith("_at") or key.endswith("_utc"):
                        try:
                            moment = parse_iso_utc(value)
                        except ValueError as exc:
                            errors.append(f"{symbol}.{section}[{index}].{key}: {exc}")
                            continue
                        if moment > cutoff_utc:
                            errors.append(
                                f"{symbol}.{section}[{index}].{key} after cutoff"
                            )
    return errors


def check_observe_only(bundle: dict) -> list:
    errors = []
    if bundle.get("mode") != "OBSERVE_ONLY_NO_ORDER":
        errors.append(f"mode={bundle.get('mode')!r}")
    for symbol, inst in bundle.get("instruments", {}).items():
        for index, candidate in enumerate(inst.get("candidates", [])):
            if candidate.get("entry_authorized") is not False:
                errors.append(f"{symbol}.candidates[{index}].entry_authorized")
    for hit in find_forbidden_keys(bundle, FORBIDDEN_TRADING_KEYS):
        errors.append(f"trading key: {hit}")
    return errors


def check_privacy(bundle: dict) -> list:
    errors = [f"private key: {hit}" for hit in find_forbidden_keys(
        bundle, FORBIDDEN_PRIVACY_KEYS
    )]
    errors.extend(f"local path: {hit}" for hit in find_local_paths(bundle))
    return errors


def check_catalog(bundle: dict, expected_symbols) -> list:
    present = set(bundle.get("instruments", {}))
    exported = set(bundle.get("exported", []))
    unavailable = set(bundle.get("unavailable", []))
    errors = []
    for symbol in expected_symbols:
        if symbol not in present:
            errors.append(f"missing-from-instruments:{symbol}")
        if symbol not in present and symbol not in unavailable:
            errors.append(f"missing-from-unavailable:{symbol}")
    if present != exported:
        errors.append(f"exported mismatch: {sorted(present ^ exported)}")
    if exported & unavailable:
        errors.append(f"exported/unavailable overlap: {sorted(exported & unavailable)}")
    return errors


def classify_feed(inst: dict, cutoff_utc: datetime, tf: str = "M15") -> str:
    """Higher timeframes follow their own close calendar; M15 must hit the cut."""
    if tf != "M15":
        return inst.get("freshness_status", "UNKNOWN")
    last = inst.get("last_bar_close_utc")
    if not last or inst.get("freshness_status") in {"STALE_FEED", "ERROR"}:
        return "STALE_FEED"
    try:
        close = parse_iso_utc(last)
    except ValueError:
        return "STALE_FEED"
    if close != cutoff_utc:
        return "STALE_FEED"
    return "FRESH"


# ---------------------------------------------------------------------------
# Deterministic, LF-normalized bundle writer + manifest verification
# ---------------------------------------------------------------------------
def normalize_lf(data: bytes) -> bytes:
    return data.replace(b"\r\n", b"\n").replace(b"\r", b"\n")


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def dumps_json(obj) -> bytes:
    return (json.dumps(obj, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")


def render_bundle(bundle: dict) -> dict:
    files = {
        "snapshot.json": dumps_json(bundle),
        "snapshot_global.md": (
            "# London 08:15 snapshot (synthetic fixture)\n\n"
            f"cutoff_utc: {bundle['snapshot_cutoff_utc']}\n"
            f"mode: {bundle['mode']}\n"
        ).encode("utf-8"),
        "data_quality.json": dumps_json({"status": "PASSED", "synthetic": True}),
    }
    for symbol in sorted(bundle.get("instruments", {})):
        files[f"instruments/{symbol}/analysis.json"] = dumps_json(
            bundle["instruments"][symbol]
        )
    return {path: normalize_lf(data) for path, data in files.items()}


def build_manifest(files: dict, bundle: dict) -> dict:
    entries = []
    for path in sorted(files):
        data = normalize_lf(files[path])
        entries.append({
            "path": path,
            "sha256": sha256(data),
            "bytes": len(data),
        })
    return {
        "schema_version": bundle["schema_version"],
        "snapshot_id": bundle["snapshot_id"],
        "snapshot_cutoff_utc": bundle["snapshot_cutoff_utc"],
        "generated_at_utc": bundle["generated_at_utc"],
        "engine_revision": bundle["engine_revision"],
        "source_repository": SOURCE_REPOSITORY,
        "provider": PROVIDER,
        "mode": bundle["mode"],
        "files": entries,
    }


def write_bundle(bundle: dict, root) -> dict:
    root = Path(root)
    files = render_bundle(bundle)
    files["manifest.json"] = dumps_json(build_manifest(files, bundle))
    files = {path: normalize_lf(data) for path, data in files.items()}
    changed, hashes = [], {}
    for path in sorted(files):
        destination = root / path
        destination.parent.mkdir(parents=True, exist_ok=True)
        data = files[path]
        hashes[path] = sha256(data)
        if not destination.exists() or destination.read_bytes() != data:
            destination.write_bytes(data)
            changed.append(path)
    bundle_hash = sha256("".join(
        f"{path}:{hashes[path]}\n" for path in sorted(hashes)
    ).encode("utf-8"))
    return {
        "changed": changed,
        "hashes": hashes,
        "bundle_sha256": bundle_hash,
        "file_count": len(files),
    }


def verify_manifest(root, manifest: dict) -> list:
    errors = []
    for entry in manifest.get("files", []):
        path = entry.get("path", "")
        target = Path(root) / path
        if not target.exists():
            errors.append(f"missing:{path}")
            continue
        data = normalize_lf(target.read_bytes())
        if sha256(data) != entry.get("sha256"):
            errors.append(f"sha256-mismatch:{path}")
        if len(data) != entry.get("bytes"):
            errors.append(f"byte-length-mismatch:{path}")
    return errors


def validate_manifest(manifest: dict) -> list:
    errors = []
    for key in sorted(MANIFEST_REQUIRED_KEYS - set(manifest)):
        errors.append(f"missing-key:{key}")
    if manifest.get("mode") != "OBSERVE_ONLY_NO_ORDER":
        errors.append("invalid-mode")
    entries = manifest.get("files")
    if not isinstance(entries, list) or not entries:
        errors.append("invalid-files-list")
        return errors
    for entry in entries:
        digest = entry.get("sha256", "")
        size = entry.get("bytes")
        if not isinstance(entry.get("path"), str) or not entry["path"]:
            errors.append("invalid-path")
        if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
            errors.append("invalid-sha256")
        if not isinstance(size, int) or isinstance(size, bool) or size < 0:
            errors.append("invalid-byte-count")
    return errors


# ---------------------------------------------------------------------------
# latest.json pointer semantics and failure-mode helpers
# ---------------------------------------------------------------------------
def latest_status(latest: dict, today: date) -> str:
    """Self-declared 'label' fields are deliberately ignored."""
    if latest.get("validation_status") != "PASSED":
        return "BLOCKED"
    try:
        snapshot_day = date.fromisoformat(latest["snapshot_date"])
    except (KeyError, ValueError, TypeError):
        return "BLOCKED"
    if snapshot_day != today:
        return "PENDIENTE DE SNAPSHOT NUEVO"
    return "NEW"


def update_latest_if_valid(current: dict, candidate: dict, *, published: bool,
                           valid: bool, today: date) -> dict:
    if published and valid and latest_status(candidate, today) == "NEW":
        return dict(candidate)
    return dict(current)


@contextmanager
def sandbox_dir():
    """A temporary directory INSIDE work_tests -- no writes outside the folder."""
    base = Path(__file__).resolve().parent / ".sandbox"
    base.mkdir(exist_ok=True)
    with TemporaryDirectory(dir=str(base), prefix="case_") as path:
        yield Path(path)
