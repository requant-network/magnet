import ctypes
from dataclasses import asdict
import os
from pathlib import Path
import sys
import tempfile
import unittest

from reference.header import LabHeader
from reference.lattice_policies import LatticeBudget
from reference.sis import Profile
from scripts.window_driver import run_window, read_snapshot
from scripts.window_worker import decode, publish
from scripts.windows_job import BasicLimit, ExtendedLimit, ProcessInfo, Startup, run_job


class WindowProtocolTests(unittest.TestCase):
    def test_immutable_markers_recover_prior_checkpoint(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            value = {"status": "running", "stages": [1]}
            publish(folder / "checkpoint-1.json", value)
            self.assertEqual(read_snapshot(folder), value)
            response = folder / "response.json"
            response.write_bytes(b'{"status":')
            self.assertEqual(read_snapshot(folder), value)
            marker = response.with_suffix(".json.ready")
            for invalid in (b"x", bytes(40), bytes(41), (8388609).to_bytes(8, "little")+bytes(32)):
                marker.write_bytes(invalid)
                self.assertEqual(read_snapshot(folder), value)
            with self.assertRaises(FileExistsError):
                publish(folder / "checkpoint-1.json", value)
            publish(folder / "error.json", {"status": "memory-error"})
            self.assertEqual(read_snapshot(folder), {"status": "memory-error"})

    def test_invalid_protocol_rejected_without_optional_backend(self):
        import json
        h = LabHeader(bytes(32), bytes(32), bytes(32), 1, 1, 0, Profile(7, 1, 2, 2))
        r = {"version": "WLP1", "policy": "all", "target": 0, "stages": [[h.encode().hex()]],
             "budget": asdict(LatticeBudget()), "cache_capacity": 16}
        self.assertEqual(decode(json.dumps(r).encode())[1][0][0], h)
        for changes in ({"target": True}, {"stages": []}, {"stages": [["00"]]}, {"policy": "unknown"},
                        {"cache_capacity": 33}, {"extra": 1}):
            with self.assertRaises(ValueError):
                decode(json.dumps(r | changes).encode())
        with self.assertRaises(ValueError):
            decode(b"x"*65537)


@unittest.skipUnless(os.name == "nt", "Windows Job Object tests")
class WindowsJobTests(unittest.TestCase):
    def test_abi_and_rejected_limits(self):
        if ctypes.sizeof(ctypes.c_void_p) == 8:
            self.assertEqual([ctypes.sizeof(t) for t in (BasicLimit, ExtendedLimit, Startup, ProcessInfo)], [64, 144, 104, 24])
        for values in ((True, 48), (0, 48), (100, 15), (100, 513)):
            with self.assertRaises(ValueError):
                run_job([sys.executable], cwd=Path.cwd(), wall_ms=values[0], memory_mib=values[1])

    def test_parent_terminates_stalled_worker(self):
        result = run_window(sys.executable, {}, wall_ms=100, memory_mib=48, diagnostic="sleep")
        self.assertEqual(result["outcome"], "wall-timeout")
        self.assertFalse(result["logical_work_known"])
        self.assertNotEqual(result["resource"]["exit_code"], 259)
        self.assertLess(result["resource"]["elapsed_ns"], 2_000_000_000)

    def test_os_denies_large_allocation(self):
        result = run_window(sys.executable, {}, wall_ms=2000, memory_mib=48, diagnostic="allocate")
        self.assertEqual(result["outcome"], "worker-memory-error")
        self.assertFalse(result["logical_work_known"])
        self.assertGreater(result["resource"]["peak_process_commit_bytes"], 0)
        self.assertLessEqual(result["resource"]["peak_process_commit_bytes"], 48*1024*1024)


if __name__ == "__main__":
    unittest.main()
