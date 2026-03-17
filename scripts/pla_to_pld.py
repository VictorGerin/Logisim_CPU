#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Convert a minimized PLA file (with .ilb/.ob headers) to a GALASM .pld file.

Usage:
  python3 scripts/pla_to_pld.py <input.pla> <config.json> <output.pld>

This is the focused PLA→PLD step used by the Makefile. It replaces the
`run_pipeline.py --pla-input` invocation with a simpler positional interface.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

_scripts_dir = Path(__file__).resolve().parent
if str(_scripts_dir) not in sys.path:
    sys.path.insert(0, str(_scripts_dir))

from run_pipeline import (  # noqa: E402
    parse_pla_headers,
    split_espresso_by_bit,
    gen_eq,
    stage_equations_from_pla,
    stage_build_pld,
)


def main(argv: list[str] | None = None) -> int:
    args = (argv if argv is not None else sys.argv[1:])
    if len(args) != 3:
        print(
            "Usage: pla_to_pld.py <input.pla> <config.json> <output.pld>",
            file=sys.stderr,
        )
        return 1

    pla_path = Path(args[0])
    json_path = Path(args[1])
    out_path = Path(args[2])

    if not pla_path.exists():
        print(f"Error: PLA file not found: {pla_path}", file=sys.stderr)
        return 1
    if not json_path.exists():
        print(f"Error: JSON config not found: {json_path}", file=sys.stderr)
        return 1

    lines = pla_path.read_text(encoding="utf-8").splitlines()
    input_labels, output_labels, pla_lines = parse_pla_headers(lines)
    if not input_labels:
        print(
            f"Error: PLA file has no '.ilb' header: {pla_path}", file=sys.stderr
        )
        return 1
    if not output_labels:
        print(
            f"Error: PLA file has no '.ob' header: {pla_path}", file=sys.stderr
        )
        return 1

    equation_blocks = stage_equations_from_pla(
        pla_lines, input_labels, output_labels, negate=False
    )

    # Apply output_splits from config if present
    try:
        cfg = json.loads(json_path.read_text(encoding="utf-8"))
        output_splits = cfg.get("output_splits") if isinstance(cfg, dict) else None
    except (OSError, json.JSONDecodeError):
        output_splits = None

    if output_splits:
        from lib import split_sop  # type: ignore

        try:
            equation_blocks = split_sop.apply_output_splits(
                equation_blocks, output_labels, output_splits, emit_tristate_gnd=False
            )
        except (split_sop.InsufficientTermsError, split_sop.ExcessTermsError) as e:
            print(f"Error: {e}", file=sys.stderr)
            return 1

    pld_text = stage_build_pld(
        equation_blocks,
        config_path=str(json_path),
        pld_device=None,
        pld_name=None,
        pld_pin=[],
        pld_desc=[],
        input_path=pla_path,
    )

    try:
        out_path.write_text(pld_text, encoding="utf-8")
    except OSError as e:
        print(f"Error writing {out_path}: {e}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
