#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Convert Espresso PLA lines to Logisim-evolution PlaRom component format.

PlaRom uses:
- AND matrix: one row per product term, one column per input.
  Value per cell: 0 = input absent, 1 = Not A, 2 = A.
  PLA mapping: '0' -> 1, '1' -> 2, '-'/x -> 0.
- OR matrix: one row per output, one column per product.
  Value 1 if that product is in the sum for that output, else 0.
"""

from __future__ import annotations

# PLA input char -> PlaRom AND cell: 0=absent, 1=Not A, 2=A
_PLA_AND: dict[str, str] = {"0": "1", "1": "2"}
# PLA output char -> PlaRom OR cell: 1=product used for that output, 0=not
_PLA_OR: dict[str, str] = {"1": "1"}


def parse_pla_lines(
    pla_lines: list[str],
) -> tuple[int, int, list[tuple[str, str]]]:
    """
    Parse Espresso PLA text (e.g. output of stage_run_espresso).

    Returns:
        (num_inputs, num_outputs, list of (input_str, output_str)).
    """
    num_inputs: int | None = None
    num_outputs: int | None = None
    terms: list[tuple[str, str]] = []

    for line in pla_lines:
        line = line.strip()
        if not line:
            continue
        if line.startswith(".i "):
            num_inputs = int(line[3:].strip())
            continue
        if line.startswith(".o "):
            num_outputs = int(line[3:].strip())
            continue
        if line.startswith("."):
            continue
        parts = line.split(None, 1)
        if len(parts) != 2:
            continue
        input_part, output_part = parts
        if num_inputs is not None and len(input_part) != num_inputs:
            raise ValueError(
                f"PLA data line has {len(input_part)} input chars, expected {num_inputs}: {line!r}"
            )
        if num_outputs is not None and len(output_part) != num_outputs:
            raise ValueError(
                f"PLA data line has {len(output_part)} output chars, expected {num_outputs}: {line!r}"
            )
        terms.append((input_part, output_part))

    if num_inputs is None:
        raise ValueError("PLA missing .i (number of inputs)")
    if num_outputs is None:
        raise ValueError("PLA missing .o (number of outputs)")
    if not terms:
        raise ValueError("PLA has no data lines")

    return (num_inputs, num_outputs, terms)


def pla_to_plarom_contents(
    num_inputs: int,
    num_outputs: int,
    terms: list[tuple[str, str]],
) -> str:
    """
    Build PlaRom Contents string from parsed PLA terms.

    AND matrix first (product by product), then OR matrix (output by output).
    Values space-separated with trailing space.
    """
    and_digits: list[str] = []
    or_digits: list[str] = []
    for inp, out in terms:
        for c in inp:
            and_digits.append(_PLA_AND.get(c, "0"))
        for o in range(num_outputs):
            or_digits.append(_PLA_OR.get(out[o] if o < len(out) else "", "0"))

    return " ".join(and_digits + or_digits) + " "


def plarom_attrs(pla_lines: list[str]) -> dict[str, int | str]:
    """
    Build full PlaRom attribute dict from PLA lines.

    Returns:
        Dict with keys: inputs, outputs, and, Contents (suitable for .circ XML).
    """
    num_inputs, num_outputs, terms = parse_pla_lines(pla_lines)
    contents = pla_to_plarom_contents(num_inputs, num_outputs, terms)
    return {
        "inputs": num_inputs,
        "outputs": num_outputs,
        "and": len(terms),
        "Contents": contents,
    }


def _xml_escape_val(val: str) -> str:
    """Escape &, <, >, " for use inside XML attribute."""
    return (
        val.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def render_plarom_xml(
    attrs: dict[str, int | str],
    loc: tuple[int, int] = (430, 290),
    label: str = "rom",
) -> str:
    """
    Render PlaRom component as Logisim-evolution .circ XML snippet.

    attrs: dict from plarom_attrs (inputs, outputs, and, Contents).
    loc: (x, y) for component position.
    label: component label.
    """
    x, y = loc
    lines = [f'    <comp lib="10" loc="({x},{y})" name="PlaRom">']
    lines.append(f'      <a name="Contents" val="{_xml_escape_val(attrs["Contents"])}"/>')
    lines.append(f'      <a name="and" val="{attrs["and"]}"/>')
    lines.append(f'      <a name="inputs" val="{attrs["inputs"]}"/>')
    lines.append(f'      <a name="label" val="{_xml_escape_val(label)}"/>')
    lines.append(f'      <a name="outputs" val="{attrs["outputs"]}"/>')
    lines.append("    </comp>")
    lines.append("")
    return "\n".join(lines)
