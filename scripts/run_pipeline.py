#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Orchestrate the pipeline:
  Logisim truth table -> PLA -> Espresso -> split per output bit -> sum-of-products equations

Equivalent to (example):
  python3 scripts/logisim_to_pla.py -i Circuits/teste.txt \
    | ./Progs/espresso-logic/bin/espresso \
    | python3 scripts/split.py 1 \
    | python3 scripts/gen_eq.py --stdin -m A2 -m A1 -m A0 -m B1 -m B0

This script does the same, but:
  - imports the Python steps as modules
  - runs Espresso via subprocess stdin/stdout
  - auto-generates map names from the truth table header (input_labels)
  - runs split + gen_eq once per output bit and prints:
      <OutputBitName> = <equation>
"""

from __future__ import annotations

import argparse
import io
import os
import shlex
import shutil
import subprocess
import sys
from pathlib import Path


def _repo_root() -> Path:
    # scripts/run_pipeline.py -> repo root is parent of scripts/
    return Path(__file__).resolve().parents[1]


def _default_espresso_cmd(repo_root: Path) -> list[str] | None:
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


def _run_espresso(cmd: list[str], pla_text: str, cwd: Path) -> str:
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


def stage_read_input(args: argparse.Namespace) -> list[str]:
    """Read Logisim input from file or STDIN. Returns list of lines."""
    if args.input:
        in_path = Path(args.input)
        if not in_path.is_absolute():
            in_path = (Path.cwd() / in_path).resolve()
        try:
            return in_path.read_text(encoding="utf-8").splitlines()
        except FileNotFoundError:
            raise SystemExit(f"Error: file not found: {in_path}")
        except OSError as e:
            raise SystemExit(f"Error reading {in_path}: {e}")
    return sys.stdin.read().splitlines()


def stage_parse_logisim(lines: list[str]) -> tuple[list[str], list[str], list[tuple[str, str]]]:
    """Parse Logisim truth table lines. Returns (input_labels, output_labels, rows)."""
    import logisim_to_pla  # type: ignore

    return logisim_to_pla.read_logisim(lines)


def stage_build_pla(
    input_labels: list[str],
    output_labels: list[str],
    rows: list[tuple[str, str]],
) -> str:
    """Build PLA text from parsed Logisim data."""
    import logisim_to_pla  # type: ignore

    pla_buf = io.StringIO()
    logisim_to_pla.write_pla(pla_buf, input_labels, output_labels, rows)
    return pla_buf.getvalue()


def stage_run_espresso(pla_text: str, espresso_cmd: list[str], cwd: Path) -> list[str]:
    """Run Espresso on PLA text. Returns minimized PLA as list of lines."""
    minimized = _run_espresso(espresso_cmd, pla_text, cwd=cwd)
    return minimized.splitlines()


def stage_equations_from_pla(
    pla_lines: list[str],
    input_labels: list[str],
    output_labels: list[str],
    negate: bool,
) -> list[str]:
    """Build equation blocks (one per output bit). Returns list of 'OutName = ...' strings."""
    import gen_eq  # type: ignore
    import split  # type: ignore

    blocks: list[str] = []
    for i, out_name in enumerate(output_labels):
        split_lines = split.split_espresso_by_bit(
            pla_lines, var_index=i, replace_dash_to_x=True
        )
        eq = gen_eq.gen_eq(split_lines, map_names=input_labels, negate=negate)
        eq_out = eq if eq.strip() else "0"
        prefix = f"{out_name} = "
        if "\n" in eq_out:
            eq_out = eq_out.replace("\n", "\n" + (" " * len(prefix)))
        blocks.append(prefix + eq_out)
    return blocks


def stage_build_pld(
    equation_blocks: list[str],
    config_path: str | None,
    pld_device: str | None,
    pld_name: str | None,
    pld_pin: list[str],
    pld_desc: list[str],
    input_path: Path | None,
) -> str:
    """Build PLD text from equation blocks and config. Returns .pld file content (no I/O)."""
    import eq_to_pld  # type: ignore

    if config_path is None and input_path is not None:
        default_config = input_path.with_suffix(".json")
        if default_config.is_file():
            config_path = str(default_config)

    equations_text = "\n\n".join(equation_blocks) + "\n" if equation_blocks else ""

    device, name, pins, desc_lines = eq_to_pld.load_pld_config(
        device_arg=pld_device,
        name_arg=pld_name,
        pin_args=pld_pin,
        desc_args=pld_desc,
        config_path=config_path,
    )
    return eq_to_pld.render_pld(
        equations_text=equations_text,
        device=device,
        name=name,
        pins=pins,
        description_lines=desc_lines,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run Logisim->PLA->Espresso->(split+gen_eq per output bit) pipeline."
    )
    parser.add_argument(
        "-i",
        "--input",
        metavar="FILE",
        help="Logisim truth table file (default: read from STDIN)",
    )
    parser.add_argument(
        "--espresso",
        metavar="PATH",
        help=(
            "Path to Espresso executable (default: try repo path, else 'espresso' on PATH)"
        ),
    )
    parser.add_argument(
        "-n",
        "--negate",
        action="store_true",
        help="Swap literals (same behavior as gen_eq.py --negate)",
    )
    parser.add_argument(
        "--pld-out",
        nargs="?",
        const="stdout",
        default=None,
        metavar="FILE",
        help="Output PLD: no arg or FILE=stdout prints to stdout; otherwise write to FILE.",
    )
    parser.add_argument(
        "--pld-config",
        metavar="JSON",
        help="JSON config for PLD (device/name/pins/description). If omitted and -i is used, uses <input_stem>.json in the same folder as -i.",
    )
    parser.add_argument(
        "--pld-device",
        metavar="DEVICE",
        help="Override PLD device (default: from config, else GAL22V10).",
    )
    parser.add_argument(
        "--pld-name",
        metavar="NAME",
        help="Override PLD name/project (required if not in config when using --pld-out).",
    )
    parser.add_argument(
        "--pld-pin",
        action="append",
        default=[],
        metavar="N=LABEL",
        help="Define or override PLD pin label (1..24). Repeat as needed. Only used with --pld-out.",
    )
    parser.add_argument(
        "--pld-desc",
        action="append",
        default=[],
        metavar="LINE",
        help="Description line (DESCRIPTION section in .pld). Overrides description from config when provided.",
    )
    args = parser.parse_args(argv)

    repo_root = _repo_root()

    # Import modules from scripts/ (same directory as this file).
    scripts_dir = Path(__file__).resolve().parent
    if str(scripts_dir) not in sys.path:
        sys.path.insert(0, str(scripts_dir))

    try:
        import logisim_to_pla  # type: ignore
        import split  # type: ignore
        import gen_eq  # type: ignore
        import eq_to_pld  # type: ignore
    except Exception as e:
        raise SystemExit(f"Error: failed to import pipeline modules: {e}") from e

    lines = stage_read_input(args)
    input_labels, output_labels, rows = stage_parse_logisim(lines)
    pla_text = stage_build_pla(input_labels, output_labels, rows)

    if args.espresso:
        espresso_cmd = [args.espresso]
    else:
        espresso_cmd = _default_espresso_cmd(repo_root)
    if not espresso_cmd:
        raise SystemExit(
            "Error: could not locate Espresso.\n"
            "Provide it with --espresso, or install Espresso on PATH.\n"
            "Note: this repo currently contains Espresso source under "
            f"{repo_root / 'Progs' / 'espresso-logic'} but may not include a built binary."
        )

    pla_lines = stage_run_espresso(pla_text, espresso_cmd, cwd=repo_root)
    equation_blocks = stage_equations_from_pla(
        pla_lines, input_labels, output_labels, negate=args.negate
    )

    if args.pld_out is None:
        for block in equation_blocks:
            print(block)
        return 0

    input_path: Path | None = None
    if args.input:
        input_path = Path(args.input)
        if not input_path.is_absolute():
            input_path = (Path.cwd() / input_path).resolve()

    pld_config_path = args.pld_config
    pld_text = stage_build_pld(
        equation_blocks,
        config_path=pld_config_path,
        pld_device=args.pld_device,
        pld_name=args.pld_name,
        pld_pin=args.pld_pin,
        pld_desc=args.pld_desc,
        input_path=input_path,
    )

    if args.pld_out == "stdout":
        sys.stdout.write(pld_text)
    else:
        out_path = Path(args.pld_out)
        if not out_path.is_absolute():
            out_path = (Path.cwd() / out_path).resolve()
        try:
            out_path.write_text(pld_text, encoding="utf-8")
        except OSError as e:
            raise SystemExit(f"Error writing PLD output to {out_path}: {e}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

