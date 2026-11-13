"""WeiDU runner and LuaJIT 2.1 test harness for chriz-bg-kits."""

from __future__ import annotations

import os
import pathlib
import subprocess

WEIDU_EXE = os.environ.get("CBK_WEIDU") or os.environ.get("BGSE_WEIDU") or r"C:\src\private\chriz-bg-rebalance\weidu.exe"


def run_weidu(args: list[str], cwd: pathlib.Path, check: bool = True) -> subprocess.CompletedProcess[str]:
    cmd = [WEIDU_EXE, *args, "--no-auto-tp2", "--noautoupdate", "--no-exit-pause"]
    res = subprocess.run(
        cmd,
        cwd=str(cwd),
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=30,
    )
    if check and res.returncode != 0:
        raise AssertionError(
            f"WeiDU failed (rc={res.returncode}): {' '.join(cmd)}\n"
            f"--- STDOUT ---\n{res.stdout}\n--- STDERR ---\n{res.stderr}"
        )
    return res
