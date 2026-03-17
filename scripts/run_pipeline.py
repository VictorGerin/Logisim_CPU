#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Orchestrate the pipeline:
  Logisim truth table -> PLA -> Espresso -> split per output bit -> sum-of-products equations

Equivalent to (example):
  python3 scripts/logisim_to_pla.py -i Circuits/teste.txt \
    | ./Progs/espresso-logic/bin/espresso \
    | (filter by output bit) \
    | (build SOP equation)

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
import json
import sys
from pathlib import Path

# Ensure scripts/ is on sys.path so that lib/ package is importable.
_scripts_dir = Path(__file__).resolve().parent
if str(_scripts_dir) not in sys.path:
    sys.path.insert(0, str(_scripts_dir))

from lib.espresso import find_espresso_cmd, run_espresso  # noqa: E402
from lib import logisim_to_pla  # noqa: E402
from lib import eq_to_pld  # noqa: E402


def _repo_root() -> Path:
    # scripts/run_pipeline.py -> repo root is parent of scripts/
    return Path(__file__).resolve().parents[1]


def split_espresso_by_bit(lines, var_index, replace_dash_to_x=True):
    """
    Filter Espresso PLA lines by output bit index.

    Keeps only lines where the output bit at var_index is '1', and returns
    lines in the form "input output_bit". Optionally replaces '-' with 'x'.
    """
    result_lines = []
    for line in lines:
        line = line.strip()
        if not line or line.startswith("."):
            continue
        parts = line.split(" ", 1)
        if len(parts) != 2:
            continue
        input_part, output_part = parts
        if var_index < 0 or var_index >= len(output_part):
            continue
        output_bit = output_part[var_index]
        if output_bit != "1":
            continue
        out_line = f"{input_part} {output_bit}"
        if replace_dash_to_x:
            out_line = out_line.replace("-", "x")
        result_lines.append(out_line)
    return result_lines


def gen_eq(lines, map_names, negate=False):
    """
    Build a sum-of-products equation string from minterm lines.

    Args:
        lines: Iterable of strings in "input [output]" format (only first token used).
        map_names: List of variable names, one per input bit position.
        negate: If True, swap literals (1 -> negated, 0 -> asserted).

    Returns:
        String of product terms separated by "+\\n".
    """
    if not map_names:
        return ""

    map_names = [name.replace('[', '').replace(']', '') for name in map_names]
    map_with_space = [f"{name} " for name in map_names]
    n = len(map_with_space)
    terms = []

    for line in lines:
        line = line.strip()
        if not line:
            continue
        input_part = line.split(None, 1)[0]
        chars = list(input_part)
        limit = min(len(chars), n)
        first_has_printed = False
        parts = []

        for i in range(limit):
            c = chars[i]
            has_value = False
            if c == "1":
                has_value = True
                prefix = "/" if negate else " "
                parts.append(f"{prefix}{map_with_space[i]}")
            elif c == "0":
                has_value = True
                prefix = " " if negate else "/"
                parts.append(f"{prefix}{map_with_space[i]}")
            else:
                # don't-care (x or -)
                parts.append(" " * (len(map_with_space[i]) + 2))

            if has_value and first_has_printed:
                parts[-1] = "*" + parts[-1]
            if has_value:
                first_has_printed = True

        term_str = "".join(p for p in parts if p)
        terms.append(term_str)

    return "+\n".join(terms)


def parse_pla_headers(lines: list[str]) -> tuple[list[str], list[str], list[str]]:
    """Parse an Espresso PLA file with headers.

    Extracts input_labels from '.ilb' and output_labels from '.ob'.
    Returns (input_labels, output_labels, data_lines) where data_lines
    contains only the product-term rows (no header directives).
    """
    input_labels: list[str] = []
    output_labels: list[str] = []
    data_lines: list[str] = []
    for line in lines:
        s = line.strip()
        if s.startswith(".ilb "):
            input_labels = s[5:].split()
        elif s.startswith(".ob "):
            output_labels = s[4:].split()
        elif s and not s.startswith("."):
            data_lines.append(s)
    return input_labels, output_labels, data_lines


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
    return logisim_to_pla.read_logisim(lines)


def stage_build_pla(
    input_labels: list[str],
    output_labels: list[str],
    rows: list[tuple[str, str]],
) -> str:
    """Build PLA text from parsed Logisim data."""
    pla_buf = io.StringIO()
    logisim_to_pla.write_pla(pla_buf, input_labels, output_labels, rows)
    return pla_buf.getvalue()


def stage_run_espresso(pla_text: str, espresso_cmd: list[str], cwd: Path) -> list[str]:
    """Run Espresso on PLA text. Returns minimized PLA as list of lines."""
    minimized = run_espresso(espresso_cmd, pla_text, cwd=cwd)
    return minimized.splitlines()


def stage_equations_from_pla(
    pla_lines: list[str],
    input_labels: list[str],
    output_labels: list[str],
    negate: bool,
) -> list[str]:
    """Build equation blocks (one per output bit). Returns list of 'OutName = ...' strings."""
    blocks: list[str] = []
    for i, out_name in enumerate(output_labels):
        split_lines = split_espresso_by_bit(
            pla_lines, var_index=i, replace_dash_to_x=True
        )
        eq = gen_eq(split_lines, map_names=input_labels, negate=negate)
        eq_out = eq if eq.strip() else "0"
        clean_name = out_name.replace('[', '').replace(']', '')
        prefix = f"{clean_name} = "
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
    if config_path is None and input_path is not None:
        default_config = input_path.with_suffix(".json")
        if default_config.is_file():
            config_path = str(default_config)

    equations_text = "\n\n".join(equation_blocks) + "\n" if equation_blocks else ""

    device, name, pins, desc_lines, registered_outputs = eq_to_pld.load_pld_config(
        device_arg=pld_device,
        name_arg=pld_name,
        pin_args=pld_pin,
        desc_args=pld_desc,
        config_path=config_path,
    )
    equations_text = eq_to_pld.apply_registered_suffix(
        equations_text, registered_outputs
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
        "--pla-input",
        action="store_true",
        help=(
            "Treat -i as an Espresso PLA file (with .ilb/.ob headers) instead of a "
            "Logisim truth table. Skips the Logisim parse and Espresso minimization "
            "stages (the PLA is used as-is)."
        ),
    )
    parser.add_argument(
        "-n",
        "--negate",
        action="store_true",
        help="Swap literals (same behavior as the --negate flag in gen_eq)",
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

    if args.pla_input:
        # PLA input mode: read an Espresso PLA file directly (e.g. from yosys).
        # Skips Logisim parsing and Espresso minimization — the PLA is already minimized.
        lines = stage_read_input(args)
        input_labels, output_labels, pla_lines = parse_pla_headers(lines)
        if not input_labels:
            raise SystemExit(
                "Error: PLA file has no '.ilb' header. "
                "Make sure the file was generated with headers (e.g. yosys write_pla)."
            )
        if not output_labels:
            raise SystemExit(
                "Error: PLA file has no '.ob' header. "
                "Make sure the file was generated with headers (e.g. yosys write_pla)."
            )
    else:
        lines = stage_read_input(args)
        input_labels, output_labels, rows = stage_parse_logisim(lines)
        pla_text = stage_build_pla(input_labels, output_labels, rows)

        if args.espresso:
            espresso_cmd = [args.espresso]
        else:
            espresso_cmd = find_espresso_cmd(repo_root)
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

    # Apply output_splits from config so that outputs with many product terms
    # are split into _Y0, _Y1, ... and Y = (direct terms) + _Y0 + _Y1 + ...
    config_path_for_splits = args.pld_config
    if config_path_for_splits is None and input_path is not None:
        default_config = input_path.with_suffix(".json")
        if default_config.is_file():
            config_path_for_splits = str(default_config)
    if config_path_for_splits:
        try:
            with open(config_path_for_splits, "r", encoding="utf-8") as f:
                cfg = json.load(f)
            output_splits = cfg.get("output_splits") if isinstance(cfg, dict) else None
        except (FileNotFoundError, OSError, json.JSONDecodeError):
            output_splits = None
    else:
        output_splits = None

    if output_splits:
        from lib import split_sop  # type: ignore

        try:
            equation_blocks = split_sop.apply_output_splits(
                equation_blocks, output_labels, output_splits, emit_tristate_gnd=False
            )
        except (split_sop.InsufficientTermsError, split_sop.ExcessTermsError) as e:
            raise SystemExit(f"Error: {e}") from e

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
