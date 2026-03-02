#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Generate a GALASM-compatible .pld file from a block of equations.

The script is intentionally dumb about the equation text: it simply
copies whatever it receives (typically the output of run_pipeline.py)
into the logic section of the .pld file.

Configuration (device, name, pins, description) can come from:
  - a JSON config file (--config), and/or
  - CLI overrides (device/name/pins/description).

JSON schema (example):
  {
    "device": "GAL22V10",
    "name": "StateMachine",
    "pins": {
      "1": "Clock",
      "2": "A3",
      ...
      "24": "VCC"
    },
    "description": [
      "Somador de 3 bits com Carry Out",
      "Out[3:0] = A[2:0] + B[2:0]"
    ]
  }
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Iterable, List, Mapping, Sequence, Tuple


def _parse_pin_arg(arg: str) -> Tuple[int, str]:
    """
    Parse a CLI pin argument of the form "N=LABEL".
    """
    if "=" not in arg:
        raise SystemExit(f"Invalid --pin value {arg!r}: expected N=LABEL")
    num_str, label = arg.split("=", 1)
    num_str = num_str.strip()
    label = label.strip()
    if not num_str:
        raise SystemExit(f"Invalid --pin value {arg!r}: pin number is empty")
    try:
        pin_num = int(num_str, 10)
    except ValueError as e:
        raise SystemExit(f"Invalid --pin value {arg!r}: {num_str!r} is not an integer") from e
    if not (1 <= pin_num <= 24):
        raise SystemExit(f"Invalid --pin value {arg!r}: pin number must be between 1 and 24")
    if not label:
        raise SystemExit(f"Invalid --pin value {arg!r}: label must not be empty")
    return pin_num, label


def _normalize_description(desc_from_config, desc_from_cli: Sequence[str]) -> List[str]:
    """
    Build the final DESCRIPTION lines.

    CLI description (if provided) overrides config description.
    """
    if desc_from_cli:
        return [str(s) for s in desc_from_cli]

    if desc_from_config is None:
        return []
    if isinstance(desc_from_config, str):
        return desc_from_config.splitlines()
    if isinstance(desc_from_config, (list, tuple)):
        return [str(s) for s in desc_from_config]
    return [str(desc_from_config)]


def load_pld_config(
    device_arg: str | None,
    name_arg: str | None,
    pin_args: Sequence[str],
    desc_args: Sequence[str],
    config_path: str | None,
) -> Tuple[str, str, List[str], List[str]]:
    """
    Merge JSON config (if any) with CLI overrides and return:
      (device, name, pins_list, description_lines)

    Precedence rules:
      - Start from JSON (if provided)
      - Apply CLI overrides on top:
          --device, --name, --pin, --desc
      - Fallback default for device: "GAL22V10" if still missing
      - Require: name, 24 pins
    """
    device: str | None = None
    name: str | None = None
    pins_map: dict[int, str] = {}
    desc_from_config = None

    if config_path:
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                cfg = json.load(f)
        except FileNotFoundError:
            raise SystemExit(f"Error: config file not found: {config_path}")
        except OSError as e:
            raise SystemExit(f"Error reading config file {config_path}: {e}")
        except json.JSONDecodeError as e:
            raise SystemExit(f"Error parsing JSON config {config_path}: {e}")

        if isinstance(cfg, Mapping):
            if "device" in cfg:
                device = str(cfg["device"])
            if "name" in cfg:
                name = str(cfg["name"])
            if "pins" in cfg:
                pins_obj = cfg["pins"]
                if not isinstance(pins_obj, Mapping):
                    raise SystemExit("Error: 'pins' in config must be an object {\"1\": \"Clock\", ...}")
                for k, v in pins_obj.items():
                    try:
                        pin_num = int(str(k), 10)
                    except ValueError:
                        raise SystemExit(f"Error: invalid pin key {k!r} in config (must be '1'..'24')")
                    if not (1 <= pin_num <= 24):
                        raise SystemExit(f"Error: pin number {pin_num} in config must be between 1 and 24")
                    pins_map[pin_num] = str(v)
            if "description" in cfg:
                desc_from_config = cfg["description"]
        else:
            raise SystemExit(f"Error: config root must be a JSON object, got {type(cfg).__name__}")

    # CLI overrides on top of config.
    if device_arg:
        device = device_arg
    if name_arg:
        name = name_arg

    for p_arg in pin_args:
        pin_num, label = _parse_pin_arg(p_arg)
        pins_map[pin_num] = label

    desc_lines = _normalize_description(desc_from_config, desc_args)

    if not device:
        device = "GAL22V10"
    if not name:
        raise SystemExit("Error: PLD name is required (use --name or provide it in the config JSON)")

    missing_pins = [i for i in range(1, 25) if i not in pins_map]
    if missing_pins:
        missing_str = ", ".join(str(i) for i in missing_pins)
        raise SystemExit(
            "Error: missing pin labels for the following pin numbers: "
            f"{missing_str}. Use --pin N=LABEL or define them in the config JSON."
        )

    pins_list = [pins_map[i] for i in range(1, 25)]
    return device, name, pins_list, desc_lines


def render_pld(
    equations_text: str,
    device: str,
    name: str,
    pins: Sequence[str],
    description_lines: Iterable[str],
) -> str:
    """
    Render a .pld file as a single string.

    - equations_text is copied verbatim (only trailing newlines are normalized).
    - pins is a sequence of 24 labels (index 0 -> pin 1, ..., index 23 -> pin 24).
    """
    if len(pins) != 24:
        raise ValueError(f"Expected 24 pin labels, got {len(pins)}")

    top_pins = pins[:12]
    bottom_pins = pins[12:]

    # Normalize equation text: ensure it ends with a single newline if non-empty.
    equations_text = equations_text.replace("\r\n", "\n")
    if equations_text:
        equations_text = equations_text.rstrip("\n") + "\n"

    lines: List[str] = []
    lines.append(str(device))
    lines.append(str(name))
    lines.append("")

    # Pin block with aligned columns (like GAL_Out1.pld).
    col_widths = []
    for i in range(12):
        w = max(
            len(str(i + 1)),
            len(str(i + 13)),
            len(top_pins[i]),
            len(bottom_pins[i]),
        )
        col_widths.append(w + 2)  # at least 2 spaces between columns

    def fmt_row(cells: Sequence[str]) -> str:
        return "".join(cells[j].ljust(col_widths[j]) for j in range(12)).rstrip()

    # Comment lines start at column 0 with ';'.
    lines.append(";" + fmt_row([str(i) for i in range(1, 13)]))
    # Pin rows start with one leading space to visually align under the numbers.
    lines.append(" " + fmt_row(top_pins))
    lines.append(" " + fmt_row(bottom_pins))
    lines.append(";" + fmt_row([str(i) for i in range(13, 25)]))
    lines.append("")
    lines.append("")

    if equations_text:
        lines.append(equations_text.rstrip("\n"))
        lines.append("")

    lines.append("DESCRIPTION")
    lines.append("")
    for d_line in description_lines:
        lines.append(str(d_line))

    # Ensure final newline.
    return "\n".join(lines).rstrip("\n") + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Generate GALASM .pld file from equations text."
    )
    parser.add_argument(
        "-i",
        "--input",
        metavar="FILE",
        help="Input file with equations (default: read from STDIN)",
    )
    parser.add_argument(
        "--stdin",
        action="store_true",
        help="Read equations from STDIN explicitly (overrides -i)",
    )
    parser.add_argument(
        "-o",
        "--output",
        metavar="FILE",
        help="Output .pld file (default: write to STDOUT)",
    )
    parser.add_argument(
        "--config",
        metavar="JSON",
        help="JSON config file with device/name/pins/description",
    )
    parser.add_argument(
        "--device",
        metavar="DEVICE",
        help="Override device (default: from config, else GAL22V10)",
    )
    parser.add_argument(
        "--name",
        metavar="NAME",
        help="Override PLD name/project (required if not in config)",
    )
    parser.add_argument(
        "-p",
        "--pin",
        action="append",
        default=[],
        metavar="N=LABEL",
        help="Define or override pin label (1..24). Repeat as needed.",
    )
    parser.add_argument(
        "-d",
        "--desc",
        action="append",
        default=[],
        metavar="LINE",
        help="Description line (DESCRIPTION section). Repeat to add multiple lines. "
        "Overrides description from config if provided.",
    )

    args = parser.parse_args(argv)

    device, name, pins, desc_lines = load_pld_config(
        device_arg=args.device,
        name_arg=args.name,
        pin_args=args.pin,
        desc_args=args.desc,
        config_path=args.config,
    )

    # Read equations text.
    if args.stdin or not args.input:
        equations_text = sys.stdin.read()
    else:
        try:
            with open(args.input, "r", encoding="utf-8") as f:
                equations_text = f.read()
        except FileNotFoundError:
            raise SystemExit(f"Error: input file not found: {args.input}")
        except OSError as e:
            raise SystemExit(f"Error reading input file {args.input}: {e}")

    pld_text = render_pld(
        equations_text=equations_text,
        device=device,
        name=name,
        pins=pins,
        description_lines=desc_lines,
    )

    if args.output:
        try:
            with open(args.output, "w", encoding="utf-8") as f:
                f.write(pld_text)
        except OSError as e:
            raise SystemExit(f"Error writing output file {args.output}: {e}")
    else:
        sys.stdout.write(pld_text)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

