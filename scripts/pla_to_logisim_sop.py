#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Convert a minimized PLA (from truth_table_to_pla.py / Espresso) into a
Logisim-evolution .circ file implementing the Sum of Products (SOP) circuit
using discrete AND, OR, and NOT gates.

Each product term becomes an AND gate (or a direct wire for single-literal terms).
Each output bit gets an OR gate collecting all terms that drive it.
Signals are routed via Logisim Tunnel components to avoid wire-crossing issues
that would arise from a physical bus layout.

Layout (left to right):
  Col A: Input pins + NOT gates, with labelled source tunnels for each signal.
  Col B: AND gates (one per active product term), stacked vertically.
  Col C: OR gates (one per output bit) + output pins.

Usage:
  python scripts/pla_to_logisim_sop.py INPUT.pla --out-circ circuit.circ
  python scripts/truth_table_to_pla.py tt.txt | \\
      python scripts/pla_to_logisim_sop.py - --out-circ circuit.circ
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# ─── Layout constants (Logisim units, grid = 10) ──────────────────────────────

# Col A: input pins and NOT gates
X_PIN_IN = 50       # Input pin loc x  (facing east → port here)
X_SRC_TUN = 130     # Source tunnel for positive signal
X_NOT_OUT = 200     # NOT gate output loc x  (size=20 → input at x-30=200)
X_NEG_TUN = 250     # Source tunnel for negated signal

# Col B: AND gates
X_AND = 550         # AND gate output loc x  (inputs at x-50=500)
X_AND_IN = 500      # AND gate input ports x  (X_AND - AND_DEPTH)
X_AND_TUN = 630     # AND-output tunnel loc x

# Col C: OR gates and output pins
X_OR = 800          # OR gate output loc x  (inputs at x-50=750)
X_OR_IN = 750       # OR gate input ports x  (X_OR - AND_DEPTH)
X_PIN_OUT = 910     # Output pin loc x  (facing west → port here)

# Vertical layout
Y_PIN_START = 100   # Y of first input pin
Y_PIN_STEP = 70     # Vertical spacing between input pins
Y_AND_EXTRA = 100   # Gap below last input pin before first AND gate row
AND_MIN_STEP = 60   # Minimum vertical pitch between AND gate centres

# Gate parameters
NOT_SIZE = 20       # <a name="size" val="20"/> for NOT gate
NOT_DEPTH = 20      # Depth from NOT output to its single input  (size=20)
GATE_SIZE = 30      # <a name="size" val="30"/> for AND/OR gates
AND_DEPTH = 50      # Depth from AND/OR output to input row  (size=30)


# ─── XML helpers ───────────────────────────────────────────────────────────────

def _esc(val: str) -> str:
    """Escape characters that are illegal inside an XML attribute value."""
    return (
        val.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _loc(x: int, y: int) -> str:
    return f"({x},{y})"


def _comp(lib: int, x: int, y: int, name: str, attrs: dict[str, str] | None = None) -> str:
    """Render a <comp> XML element with optional <a> child attributes."""
    parts = [f'  <comp lib="{lib}" loc="{_loc(x, y)}" name="{_esc(name)}">']
    for k, v in (attrs or {}).items():
        parts.append(f'    <a name="{_esc(k)}" val="{_esc(v)}"/>')
    parts.append("  </comp>")
    return "\n".join(parts)


def _wire(x1: int, y1: int, x2: int, y2: int) -> str:
    return f'  <wire from="{_loc(x1, y1)}" to="{_loc(x2, y2)}"/>'


def _tunnel(x: int, y: int, label: str, facing: str = "east") -> str:
    return _comp(0, x, y, "Tunnel", {"facing": facing, "label": label})


def _pin_in(x: int, y: int, label: str) -> str:
    return _comp(0, x, y, "Pin", {"appearance": "classic", "label": label})


def _pin_out(x: int, y: int, label: str) -> str:
    return _comp(0, x, y, "Pin", {
        "appearance": "classic",
        "facing": "west",
        "label": label,
        "type": "output",
    })


def _not_gate(x: int, y: int) -> str:
    return _comp(1, x, y, "NOT Gate", {"size": str(NOT_SIZE)})


def _and_gate(x: int, y: int, n_inputs: int) -> str:
    return _comp(1, x, y, "AND Gate", {"inputs": str(n_inputs), "size": str(GATE_SIZE)})


def _or_gate(x: int, y: int, n_inputs: int) -> str:
    return _comp(1, x, y, "OR Gate", {"inputs": str(n_inputs), "size": str(GATE_SIZE)})


def _constant(x: int, y: int, value: int) -> str:
    return _comp(0, x, y, "Constant", {"value": hex(value)})


# ─── Gate port geometry ────────────────────────────────────────────────────────

def gate_input_dy(n: int) -> list[int]:
    """
    Y offsets (relative to the gate's output loc) for each input port of an
    n-input AND/OR gate (size=30, facing east).

    Formula: dy[i] = round((i - (n-1)/2) * 10)
    Examples:
      n=1 → [0]
      n=2 → [-5, 5]
      n=3 → [-10, 0, 10]
      n=4 → [-15, -5, 5, 15]
    """
    return [int(round((i - (n - 1) / 2.0) * 10)) for i in range(n)]


# ─── PLA parsing ───────────────────────────────────────────────────────────────

def parse_pla(lines: list[str]) -> tuple[list[str], list[str], list[tuple[str, str]]]:
    """
    Parse a PLA file (full PLA with headers, or data-lines-only output from
    truth_table_to_pla.py).

    Returns:
        input_labels  – list of N signal names
        output_labels – list of M output names
        terms         – list of (input_pattern, output_pattern) where each
                        character is '0', '1', or '-'
    """
    input_labels: list[str] | None = None
    output_labels: list[str] | None = None
    n_inputs: int | None = None
    n_outputs: int | None = None
    terms: list[tuple[str, str]] = []

    for raw in lines:
        s = raw.strip()
        if not s or s.startswith("#"):
            continue
        if s.startswith(".i "):
            n_inputs = int(s[3:].strip())
        elif s.startswith(".o "):
            n_outputs = int(s[3:].strip())
        elif s.startswith(".ilb "):
            input_labels = s[5:].split()
        elif s.startswith(".ob "):
            output_labels = s[4:].split()
        elif s.startswith("."):
            continue  # .p, .e, comments …
        else:
            parts = s.split(None, 1)
            if len(parts) == 2:
                terms.append((parts[0], parts[1]))

    if not terms:
        raise ValueError("No PLA data lines found in input")

    # Infer widths from first term when headers are absent
    if n_inputs is None:
        n_inputs = len(terms[0][0])
    if n_outputs is None:
        n_outputs = len(terms[0][1])

    if input_labels is None:
        input_labels = [f"in{i}" for i in range(n_inputs)]
    if output_labels is None:
        output_labels = [f"out{i}" for i in range(n_outputs)]

    # Validate widths
    for inp, out in terms:
        if len(inp) != n_inputs:
            raise ValueError(
                f"Input pattern width {len(inp)} ≠ {n_inputs}: {inp!r}"
            )
        if len(out) != n_outputs:
            raise ValueError(
                f"Output pattern width {len(out)} ≠ {n_outputs}: {out!r}"
            )

    return input_labels, output_labels, terms


# ─── Circuit builder ───────────────────────────────────────────────────────────

_CIRC_HEADER = """\
<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<project source="4.1.0" version="1.0">
  This file is intended to be loaded by Logisim-evolution v4.1.0(https://github.com/logisim-evolution/).

  <lib desc="#Wiring" name="0">
    <tool name="Pin">
      <a name="appearance" val="classic"/>
    </tool>
  </lib>
  <lib desc="#Gates" name="1"/>
  <lib desc="#Plexers" name="2"/>
  <lib desc="#Arithmetic" name="3"/>
  <lib desc="#FPArithmetic" name="4"/>
  <lib desc="#Memory" name="5"/>
  <lib desc="#I/O" name="6"/>
  <lib desc="#TTL" name="7"/>
  <lib desc="#TCL" name="8"/>
  <lib desc="#Base" name="9"/>
  <lib desc="#BFH-Praktika" name="10"/>
  <lib desc="#Input/Output-Extra" name="11"/>
  <lib desc="#Soc" name="12"/>
  <main name="{name}"/>
  <options>
    <a name="gateUndefined" val="error"/>
    <a name="simlimit" val="10000"/>
  </options>
  <circuit name="{name}">
    <a name="appearance" val="logisim_evolution"/>
"""

_CIRC_FOOTER = """\
  </circuit>
</project>
"""


def _active_bits(inp: str) -> list[tuple[int, str]]:
    """Return [(bit_index, char), …] for each non-don't-care bit in inp."""
    return [(k, c) for k, c in enumerate(inp) if c in "01"]


def build_circuit(
    input_labels: list[str],
    output_labels: list[str],
    terms: list[tuple[str, str]],
    circuit_name: str = "sop",
) -> str:
    """Build the full Logisim-evolution .circ XML for the SOP circuit."""

    N = len(input_labels)
    M = len(output_labels)
    elems: list[str] = []

    def add(s: str) -> None:
        elems.append(s)

    # ── Col A: Input pins + NOT gates ────────────────────────────────────────
    for i, label in enumerate(input_labels):
        y = Y_PIN_START + i * Y_PIN_STEP

        # Input pin (facing east by default – port at loc)
        add(_pin_in(X_PIN_IN, y, label))
        # Wire: pin → positive source tunnel
        add(_wire(X_PIN_IN, y, X_SRC_TUN, y))
        # Source tunnel for the positive signal  (east → visually points right)
        add(_tunnel(X_SRC_TUN, y, label, "east"))
        # Wire: positive source tunnel → NOT gate input  (depth=30 → input at X_NOT_OUT - 30)
        add(_wire(X_SRC_TUN, y, X_NOT_OUT - NOT_DEPTH, y))
        # NOT gate  (output loc = X_NOT_OUT)
        add(_not_gate(X_NOT_OUT, y))
        # Wire: NOT output → negated source tunnel
        add(_wire(X_NOT_OUT, y, X_NEG_TUN, y))
        # Source tunnel for the negated signal
        add(_tunnel(X_NEG_TUN, y, f"{label}_n", "west"))

    print(terms)

    # ── Filter terms that drive at least one output ───────────────────────────
    active_terms = [(inp, out) for inp, out in terms if "1" in out]

    # ── Compute AND gate vertical layout ─────────────────────────────────────
    k_max = max(
        (len(_active_bits(inp)) for inp, _ in active_terms),
        default=1,
    )

    and_step = max(k_max * 10 + 20, AND_MIN_STEP)
    y_and_start = Y_PIN_START + N * Y_PIN_STEP + Y_AND_EXTRA
    and_y = [y_and_start + j * and_step for j in range(len(active_terms))]

    print(and_y)

    # ── Col B: AND gates ──────────────────────────────────────────────────────
    # term_tun[j] = tunnel label that carries term j's output signal.
    term_tun: list[str] = []

    for j, (inp, _out) in enumerate(active_terms):
        y_and = and_y[j]
        actives = _active_bits(inp)
        K = len(actives)
        tun = f"_t{j}"

        if K == 0:
            # All inputs are don't-care → this term is always 1.
            # Place a Constant(1) and wire it to the term tunnel.
            add(_constant(X_AND - 30, y_and, 1))
            add(_wire(X_AND - 30, y_and, X_AND_TUN, y_and))
            add(_tunnel(X_AND_TUN, y_and, tun, "east"))

        elif K == 1:
            # Single-literal term → no AND gate needed.
            # Place a receive tunnel at X_AND that picks up the signal,
            # then wire it across to the term output tunnel.
            bit_idx, char = actives[0]
            sig = input_labels[bit_idx] if char == "1" else f"{input_labels[bit_idx]}_n"
            add(_tunnel(X_AND, y_and, sig, "west"))
            add(_wire(X_AND, y_and, X_AND_TUN, y_and))
            add(_tunnel(X_AND_TUN, y_and, tun, "east"))

        else:
            # Multi-literal term: one AND gate.
            add(_and_gate(X_AND, y_and, K))
            # Output wire + tunnel
            add(_wire(X_AND, y_and, X_AND_TUN, y_and))
            add(_tunnel(X_AND_TUN, y_and, tun, "east"))
            # Place a receive tunnel at each AND input port.
            dy_list = gate_input_dy(K)
            for port_i, (bit_idx, char) in enumerate(actives):
                sig = (
                    input_labels[bit_idx] if char == "1"
                    else f"{input_labels[bit_idx]}_n"
                )
                px, py = X_AND_IN, y_and + dy_list[port_i]
                # Facing west → visually points toward the gate on the right
                add(_tunnel(px, py, sig, "west"))

        term_tun.append(tun)

    # ── Compute which terms contribute to each output ────────────────────────
    contributing: list[list[int]] = []
    for m in range(M):
        contrib = [
            j for j, (_, out) in enumerate(active_terms)
            if m < len(out) and out[m] == "1"
        ]
        contributing.append(contrib)

    # ── Compute OR gate Y positions ───────────────────────────────────────────
    # Centre each OR gate on the mean Y of its contributing AND gates.
    # Fall back to even distribution when there are no active terms.
    y_fallback_start = y_and_start
    or_y: list[int] = []
    used_y: set[int] = set()

    for m in range(M):
        contrib = contributing[m]
        if contrib and active_terms:
            cy = sum(and_y[j] for j in contrib) // len(contrib)
        else:
            cy = y_fallback_start + m * AND_MIN_STEP

        # Nudge downward if position is already taken (10-unit steps)
        while cy in used_y:
            cy += 10
        used_y.add(cy)
        or_y.append(cy)

    # ── Col C: OR gates + output pins ────────────────────────────────────────
    for m, label in enumerate(output_labels):
        y_or = or_y[m]
        contrib = contributing[m]
        L = len(contrib)

        if L == 0:
            # Output is constant 0 – no terms produce it.
            add(_constant(X_OR - 40, y_or, 0))
            add(_wire(X_OR - 40, y_or, X_PIN_OUT, y_or))
            add(_pin_out(X_PIN_OUT, y_or, label))

        elif L == 1:
            # Only one contributing term – no OR gate needed.
            tun = term_tun[contrib[0]]
            add(_tunnel(X_OR, y_or, tun, "west"))
            add(_wire(X_OR, y_or, X_PIN_OUT, y_or))
            add(_pin_out(X_PIN_OUT, y_or, label))

        else:
            # Multiple contributing terms → OR gate.
            add(_or_gate(X_OR, y_or, L))
            add(_wire(X_OR, y_or, X_PIN_OUT, y_or))
            add(_pin_out(X_PIN_OUT, y_or, label))
            dy_list = gate_input_dy(L)
            for port_i, j in enumerate(contrib):
                tun = term_tun[j]
                px, py = X_OR_IN, y_or + dy_list[port_i]
                add(_tunnel(px, py, tun, "west"))

    # ── Assemble full .circ XML ───────────────────────────────────────────────
    body = "\n".join(elems)
    return _CIRC_HEADER.format(name=circuit_name) + body + "\n" + _CIRC_FOOTER


# ─── CLI entry point ───────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Convert a minimized PLA to a Logisim-evolution SOP circuit (.circ). "
            "Each product term becomes an AND gate; each output gets an OR gate."
        )
    )
    parser.add_argument(
        "pla_file",
        metavar="FILE",
        help="PLA file (data-lines-only or full PLA with headers); use '-' for stdin",
    )
    parser.add_argument(
        "--out-circ",
        metavar="FILE",
        type=Path,
        default=None,
        help="Output .circ file (default: write to stdout)",
    )
    parser.add_argument(
        "--circuit-name",
        metavar="NAME",
        default="sop",
        help="Logisim circuit name (default: sop)",
    )
    args = parser.parse_args()

    # Read input
    if args.pla_file == "-":
        lines = sys.stdin.read().splitlines()
    else:
        p = Path(args.pla_file)
        if not p.exists():
            print(f"Error: file not found: {p}", file=sys.stderr)
            return 1
        try:
            lines = p.read_text(encoding="utf-8").splitlines()
        except OSError as e:
            print(f"Error reading {p}: {e}", file=sys.stderr)
            return 1

    # Parse PLA
    try:
        input_labels, output_labels, terms = parse_pla(lines)
    except ValueError as e:
        print(f"Error parsing PLA: {e}", file=sys.stderr)
        return 1

    active = [t for t in terms if "1" in t[1]]
    print(
        f"Inputs: {len(input_labels)}  Outputs: {len(output_labels)}  "
        f"Terms: {len(terms)} ({len(active)} with active outputs)",
        file=sys.stderr,
    )

    # Generate circuit XML
    circ_xml = build_circuit(input_labels, output_labels, terms, args.circuit_name)

    # Write output
    if args.out_circ is not None:
        try:
            args.out_circ.write_text(circ_xml, encoding="utf-8")
            print(f"Wrote circuit to {args.out_circ}", file=sys.stderr)
        except OSError as e:
            print(f"Error writing {args.out_circ}: {e}", file=sys.stderr)
            return 1
    else:
        print(circ_xml, end="")

    return 0


if __name__ == "__main__":
    sys.exit(main())
