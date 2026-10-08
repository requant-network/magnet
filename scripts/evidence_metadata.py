"""Consolidate recorded worker metadata and verify measured source fingerprints locally."""

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ("portfolio-v1", "soak-v1", "portfolio-complete-probe-v1", "rejection-cost-v1",
           "lab-chain-v1", "native-legacy-regressions-v3", "endurance-fuzz-v1")
UNUSED_FUZZ_SOURCES = {"crates/sis-verifier/src/search.rs", "crates/sis-verifier/src/search_main.rs"}


def run():
    # Fixed local query deliberately excludes machine/user identifiers and serials.
    command = "$c = Get-CimInstance Win32_Processor; $m = Get-CimInstance Win32_ComputerSystem; " \
              "@{cpu=$c.Name; cores=$c.NumberOfCores; threads=$c.NumberOfLogicalProcessors; " \
              "physical_memory_bytes=$m.TotalPhysicalMemory} | ConvertTo-Json -Compress"
    hardware = json.loads(subprocess.check_output(["powershell", "-NoProfile", "-Command", command], text=True, timeout=15))
    prepared = []
    for name in REPORTS:
        path = ROOT / "docs/research/results" / f"{name}.json"
        report = json.loads(path.read_text(encoding="utf-8"))
        if report.get("status") not in ("passed", "completed"):
            raise RuntimeError(f"cannot consolidate incomplete evidence: {name}")
        hashes = report.get("source_sha256", report.get("current_source_sha256"))
        changed = [key for key, value in hashes.items()
                   if hashlib.sha256((ROOT / key).read_bytes()).hexdigest() != value]
        if changed and (name != "endurance-fuzz-v1" or set(changed) != UNUSED_FUZZ_SOURCES):
            raise RuntimeError(f"unexpected measured-source change: {name}: {changed}")
        report["hardware"] = hardware
        report["postprocess_script_sha256"] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
        report["measured_source_hashes_checked"] = len(hashes)
        if name in ("portfolio-v1", "soak-v1"):
            raw = json.loads((ROOT / "artifacts" / f"{name}.json").read_text(encoding="utf-8"))
            metadata = [record["window"]["snapshot"].get("backend", {}).get("flint") for record in raw["records"]
                        if record["window"]["snapshot"] is not None]
            flint = [item for item in metadata if item is not None]
            if not flint or any(item != flint[0] for item in flint):
                raise RuntimeError("optional backend metadata changed")
            report["observed_flint_backend"] = flint[0]
            report["host_load_note"] = "Portfolio and soak overlapped each other, endurance fuzz and local regressions; no isolated timing ranking."
        if name == "endurance-fuzz-v1":
            executable = ROOT / "target/debug/sis-lab.exe"
            if hashlib.sha256(executable.read_bytes()).hexdigest() != report["executable_sha256"]:
                raise RuntimeError("endurance executable changed before provenance consolidation")
            last_write = datetime.fromtimestamp(executable.stat().st_mtime, timezone.utc)
            report["native_build_profile"] = "debug"
            report["executable_last_write_utc"] = last_write.isoformat()
            report["campaign_timestamp_check"] = "unavailable: actual run-start UTC was not recorded"
            report["admission_sources_unchanged"] = True
            report["unrelated_changed_sources"] = changed
            report["provenance_note"] = (
                "Workflow provenance: original sis-lab executable was retained for the entire timed run. "
                "The recorded hash was verified before the final rebuild; the last-write timestamp is factual metadata, "
                "not an automated interval guarantee because actual run-start UTC was not recorded. "
                "Only non-executed native-search sources changed; "
                "all recorded Python and native admission sources match. New builds used artifacts/admission-current. "
                "The broad source_unchanged flag remains false; it is not overwritten or presented as a whole-repository freeze.")
        prepared.append((path, report))
    for path, report in prepared:
        path.write_text(json.dumps(report, indent=2)+"\n", encoding="utf-8")
        print(f"verified metadata: {path.name}")


if __name__ == "__main__":
    run()
