"""Windows-only suspended launch, enforced private-commit ceiling and external deadline."""

import ctypes as C
from ctypes import wintypes as W
import os
from pathlib import Path
import subprocess
import time


class BasicLimit(C.Structure):
    _fields_ = [("process_time", C.c_int64), ("job_time", C.c_int64), ("flags", W.DWORD),
                ("min_ws", C.c_size_t), ("max_ws", C.c_size_t), ("active", W.DWORD),
                ("affinity", C.c_size_t), ("priority", W.DWORD), ("scheduling", W.DWORD)]


class IOCounters(C.Structure):
    _fields_ = [(name, C.c_uint64) for name in ("read_ops", "write_ops", "other_ops", "read_bytes", "write_bytes", "other_bytes")]


class ExtendedLimit(C.Structure):
    _fields_ = [("basic", BasicLimit), ("io", IOCounters), ("process_memory", C.c_size_t),
                ("job_memory", C.c_size_t), ("peak_process", C.c_size_t), ("peak_job", C.c_size_t)]


class Startup(C.Structure):
    _fields_ = [("cb", W.DWORD), ("reserved", W.LPWSTR), ("desktop", W.LPWSTR), ("title", W.LPWSTR),
                *[(name, W.DWORD) for name in ("x", "y", "x_size", "y_size", "x_chars", "y_chars", "fill", "flags")],
                ("show", W.WORD), ("reserved_size", W.WORD), ("reserved_bytes", C.POINTER(C.c_byte)),
                ("stdin", W.HANDLE), ("stdout", W.HANDLE), ("stderr", W.HANDLE)]


class ProcessInfo(C.Structure):
    _fields_ = [("process", W.HANDLE), ("thread", W.HANDLE), ("pid", W.DWORD), ("tid", W.DWORD)]


def _api():
    dll = C.WinDLL("kernel32", use_last_error=True)
    signatures = {
        "CreateJobObjectW": ([C.c_void_p, W.LPCWSTR], W.HANDLE),
        "SetInformationJobObject": ([W.HANDLE, C.c_int, C.c_void_p, W.DWORD], W.BOOL),
        "QueryInformationJobObject": ([W.HANDLE, C.c_int, C.c_void_p, W.DWORD, C.c_void_p], W.BOOL),
        "CreateProcessW": ([W.LPCWSTR, W.LPWSTR, C.c_void_p, C.c_void_p, W.BOOL, W.DWORD,
                            C.c_void_p, W.LPCWSTR, C.POINTER(Startup), C.POINTER(ProcessInfo)], W.BOOL),
        "AssignProcessToJobObject": ([W.HANDLE, W.HANDLE], W.BOOL),
        "ResumeThread": ([W.HANDLE], W.DWORD),
        "WaitForSingleObject": ([W.HANDLE, W.DWORD], W.DWORD),
        "GetExitCodeProcess": ([W.HANDLE, C.POINTER(W.DWORD)], W.BOOL),
        "TerminateProcess": ([W.HANDLE, W.DWORD], W.BOOL),
        "TerminateJobObject": ([W.HANDLE, W.DWORD], W.BOOL),
        "CloseHandle": ([W.HANDLE], W.BOOL),
    }
    for name, (arguments, result) in signatures.items():
        method = getattr(dll, name)
        method.argtypes, method.restype = arguments, result
    return dll


def _check(value):
    if not value:
        raise C.WinError(C.get_last_error())
    return value


def run_job(command, *, cwd, wall_ms, memory_mib):
    if os.name != "nt":
        raise RuntimeError("Windows Job Objects required; no cooperative fallback")
    if (type(wall_ms) is not int or not 10 <= wall_ms <= 30_000
            or type(memory_mib) is not int or not 16 <= memory_mib <= 512
            or type(command) not in (list, tuple) or not 1 <= len(command) <= 16
            or any(type(x) is not str or not x or "\0" in x for x in command)):
        raise ValueError("invalid external resource window")
    wire = subprocess.list2cmdline(command)
    if len(wire) >= 32767:
        raise ValueError("Windows command length")
    dll, info, assigned = _api(), ProcessInfo(), False
    job = _check(dll.CreateJobObjectW(None, None))
    try:
        limits = ExtendedLimit()
        # PROCESS_MEMORY | JOB_MEMORY | KILL_ON_JOB_CLOSE. No breakaway flags.
        limits.basic.flags = 0x100 | 0x200 | 0x2000
        limits.process_memory = limits.job_memory = memory_mib*1024*1024
        _check(dll.SetInformationJobObject(job, 9, C.byref(limits), C.sizeof(limits)))
        startup = Startup(cb=C.sizeof(Startup), flags=1, show=0)
        # Do not let Python/native imports run before the memory limit is assigned.
        _check(dll.CreateProcessW(None, C.create_unicode_buffer(wire), None, None, False,
                                 0x4 | 0x08000000, None, str(Path(cwd).resolve()), C.byref(startup), C.byref(info)))
        _check(dll.AssignProcessToJobObject(job, info.process))
        assigned = True
        start = time.perf_counter_ns()
        if dll.ResumeThread(info.thread) == 0xffffffff:
            raise C.WinError(C.get_last_error())
        remaining = max(0, wall_ms-(time.perf_counter_ns()-start+999_999)//1_000_000)
        state = dll.WaitForSingleObject(info.process, remaining)
        timed_out = state == 258
        if timed_out:
            _check(dll.TerminateJobObject(job, 1))
            if dll.WaitForSingleObject(info.process, 5000) != 0:
                raise RuntimeError("terminated worker did not exit")
        elif state != 0:
            raise C.WinError(C.get_last_error())
        elapsed = time.perf_counter_ns()-start
        exit_code = W.DWORD()
        _check(dll.GetExitCodeProcess(info.process, C.byref(exit_code)))
        measured = ExtendedLimit()
        _check(dll.QueryInformationJobObject(job, 9, C.byref(measured), C.sizeof(measured), None))
        return {"status": "wall-timeout" if timed_out else "exited", "exit_code": exit_code.value,
                "pid": info.pid, "wall_ms": wall_ms, "memory_mib": memory_mib,
                "elapsed_ns": elapsed, "deadline_overshoot_ns": max(0, elapsed-wall_ms*1_000_000),
                "peak_process_commit_bytes": measured.peak_process, "peak_job_commit_bytes": measured.peak_job}
    finally:
        if info.process:
            # Also terminate descendants of a worker that exited normally.
            if assigned:
                dll.TerminateJobObject(job, 1)
            else:
                dll.TerminateProcess(info.process, 1)
            dll.WaitForSingleObject(info.process, 5000)
        for handle in (info.thread, info.process, job):
            if handle:
                dll.CloseHandle(handle)
