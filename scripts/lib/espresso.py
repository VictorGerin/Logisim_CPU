#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Helpers for locating and invoking the Espresso logic minimizer.
"""

from __future__ import annotations

import os
import shlex
import shutil
import subprocess
from pathlib import Path


def find_espresso_cmd(repo_root: Path) -> list[str] | None:
    # Expected location in this repo (may or may not exist).
    candidates = [
        repo_root / "Progs" / "espresso-logic" / "bin" / "espresso.exe",
        repo_root / "Progs" / "espresso-logic" / "bin" / "espresso",
    ]
    for p in candidates:
        if p.exists():
            return [str(p)]

    # Fallback: espresso available on PATH
    which = shutil.which("espresso")
    if which:
        return [which]

    return None


def _win_to_wsl_path(p: Path) -> str:
    # Convert "C:\\Users\\me\\repo" -> "/mnt/c/Users/me/repo"
    posix = p.resolve().as_posix()  # "C:/Users/..."
    if len(posix) >= 2 and posix[1] == ":":
        drive = posix[0].lower()
        rest = posix[2:]  # "/Users/..."
        return f"/mnt/{drive}{rest}"
    return posix


def _wsl_bash_line(cmd: list[str], cwd: Path) -> str:
    linux_cwd = _win_to_wsl_path(cwd)

    quoted: list[str] = []
    for arg in cmd:
        # If user passed an absolute Windows path, translate it.
        try:
            p = Path(arg)
            if p.drive:
                arg = _win_to_wsl_path(p)
        except Exception:
            pass
        quoted.append(shlex.quote(arg))

    return f"cd {shlex.quote(linux_cwd)} && " + " ".join(quoted)


def run_espresso(cmd: list[str], pla_text: str, cwd: Path) -> str:
    try:
        proc = subprocess.run(
            cmd,
            input=pla_text,
            text=True,
            encoding="utf-8",
            errors="replace",
            capture_output=True,
            cwd=str(cwd),
        )
    except FileNotFoundError as e:
        raise SystemExit(
            "Error: Espresso executable not found.\n"
            f"  Command: {cmd!r}\n"
            "Provide it with --espresso, or build/install Espresso."
        ) from e
    except OSError as e:
        # Common Windows case: trying to run an ELF (Linux) binary directly.
        if os.name == "nt" and getattr(e, "winerror", None) == 193 and shutil.which("wsl"):
            wsl_cmd = ["wsl", "bash", "-lc", _wsl_bash_line(cmd, cwd=cwd)]
            proc = subprocess.run(
                wsl_cmd,
                input=pla_text,
                text=True,
                encoding="utf-8",
                errors="replace",
                capture_output=True,
            )
        else:
            raise SystemExit(f"Error: failed to start Espresso: {e}") from e

    if proc.returncode != 0:
        stderr = (proc.stderr or "").strip()
        msg = "Error: Espresso failed (non-zero exit code)."
        if stderr:
            msg += "\n\n--- Espresso stderr ---\n" + stderr
        raise SystemExit(msg)

    return proc.stdout or ""
