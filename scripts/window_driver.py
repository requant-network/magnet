"""One controlled worker in a Windows Job; aborted logical work is unknown, not zero."""

import json
import hashlib
from pathlib import Path
import tempfile

from scripts.windows_job import run_job
from scripts.window_worker import MAX_INPUT, MAX_OUTPUT

ROOT = Path(__file__).resolve().parents[1]


def read_snapshot(folder):
    """Recover the latest complete bounded snapshot, never a partial write."""
    for name in ("error.json", "response.json", *(f"checkpoint-{i}.json" for i in range(8, 0, -1))):
        path = folder / name
        marker_path = path.with_suffix(path.suffix + ".ready")
        if not marker_path.exists() or not path.exists():
            continue
        with marker_path.open("rb") as stream:
            marker = stream.read(41)
        if len(marker) != 40 or int.from_bytes(marker[:8], "little") > MAX_OUTPUT:
            continue
        with path.open("rb") as stream:
            wire = stream.read(MAX_OUTPUT+1)
        if len(wire) != int.from_bytes(marker[:8], "little") or hashlib.sha256(wire).digest() != marker[8:]:
            continue
        snapshot = json.loads(wire)
        if type(snapshot) is not dict:
            raise ValueError("window response type")
        return snapshot
    return None


def run_window(python, request, *, wall_ms, memory_mib, diagnostic=None, worker="window_worker.py"):
    payload = json.dumps(request, separators=(",", ":")).encode()
    if (len(payload) > MAX_INPUT or diagnostic not in (None, "sleep", "allocate")
            or worker not in ("window_worker.py", "portfolio_worker.py")
            or worker != "window_worker.py" and diagnostic is not None):
        raise ValueError("window driver input/diagnostic")
    (ROOT / "artifacts").mkdir(exist_ok=True)
    # Preserve per-attempt evidence. Windows can briefly retain file locks after
    # forced termination; deleting in the measurement path can fail or distort it.
    directory = tempfile.mkdtemp(prefix="window-", dir=ROOT / "artifacts")
    folder = Path(directory).resolve()
    if not folder.is_relative_to((ROOT / "artifacts").resolve()):
        raise RuntimeError("window temporary path escaped artifacts")
    source, destination = folder / "request.json", folder / "response.json"
    source.write_bytes(payload)
    command = [str(python), str(ROOT / "scripts" / worker), str(source), str(destination)]
    if diagnostic is not None:
        command.append(diagnostic)
    resource = run_job(command, cwd=ROOT, wall_ms=wall_ms, memory_mib=memory_mib)
    snapshot = read_snapshot(folder)
    if snapshot is not None and snapshot.get("status") == "worker-error":
        raise RuntimeError(f"window worker error: {snapshot['error_type']}: {snapshot['message']}")
    if resource["status"] == "wall-timeout":
        outcome = "wall-timeout"
    elif resource["exit_code"] == 77 and snapshot == {"status": "memory-error"}:
        outcome = "worker-memory-error"
    elif resource["exit_code"] == 0 and snapshot is not None and snapshot.get("status") in ("completed", "diagnostic-complete"):
        outcome = "completed"
    else:
        outcome = "worker-failed-unclassified"
    return {"outcome": outcome, "resource": resource, "snapshot": snapshot,
            "artifact_directory": folder.relative_to(ROOT).as_posix(),
            "logical_work_known": outcome == "completed"}
