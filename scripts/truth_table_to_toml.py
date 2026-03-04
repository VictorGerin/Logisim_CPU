#!/usr/bin/env python3
"""
Convert Logisim truth table (.txt) + chip pinout (.json) to xgpro-logic TOML.
Usage: python truth_table_to_toml.py <truth_table.txt> <pinout.json> [-o output.toml]
"""

import argparse
import json
import re
import sys
from pathlib import Path

MAX_VECTORS_PER_CHUNK = 512


# --- Truth table parsing ---

def _strip_comment(line: str) -> str:
    i = line.find("#")
    return line[:i].strip() if i >= 0 else line.strip()


def _parse_header_token(token: str) -> list[str]:
    """Parse a single column token like 'A[2..0]', 'B[1..0]', or single-bit 'A', 'B' into ordered signal names (MSB first).
    Single-bit: 'A', 'B' or 'A[0..0]', 'B[0..0]' → returns [name] only (e.g. ['A'], ['B'])."""
    token = token.strip()
    if not token:
        return []
    m = re.match(r"(\w+)\[(\d+)\.\.(\d+)\]", token)
    if m:
        name, hi, lo = m.group(1), int(m.group(2)), int(m.group(3))
        if hi < lo:
            hi, lo = lo, hi
        n = hi - lo + 1
        if n == 1:
            return [name]
        return [f"{name}{i}" for i in range(hi, lo - 1, -1)]
    return [token]


def parse_header(header_line: str) -> tuple[list[str], list[str]]:
    """Parse header line 'A[2..0] B[1..0] | S[2..0]' -> (input_signals, output_signals)."""
    if "|" not in header_line:
        raise ValueError("Header line must contain '|' separating inputs and outputs")
    left, right = header_line.split("|", 1)
    input_tokens = left.split()
    output_tokens = right.split()
    input_signals = []
    for t in input_tokens:
        input_signals.extend(_parse_header_token(t))
    output_signals = []
    for t in output_tokens:
        output_signals.extend(_parse_header_token(t))
    return input_signals, output_signals


def _char_to_value(c: str) -> str | None:
    """Map a character from the table to logic value or don't care."""
    c = c.upper()
    if c in ("0", "1"):
        return c
    if c in ("X", "-"):
        return "X"
    return None


def parse_data_line(line: str, input_signals: list[str], output_signals: list[str]) -> dict[str, str] | None:
    """
    Parse one data line into a dict of signal_name -> '0'|'1'|'X'.
    Returns None if the line is empty or invalid.
    """
    line = line.replace(" ", "")
    if "|" not in line:
        return None
    left, right = line.split("|", 1)
    left, right = left.strip(), right.strip()
    n_in, n_out = len(input_signals), len(output_signals)
    if len(left) != n_in or len(right) != n_out:
        return None
    row = {}
    for i, sig in enumerate(input_signals):
        v = _char_to_value(left[i])
        row[sig] = v if v else "X"
    for i, sig in enumerate(output_signals):
        v = _char_to_value(right[i])
        row[sig] = v if v else "X"
    return row


def parse_truth_table(path: Path) -> tuple[list[str], list[str], list[dict[str, str]]]:
    """
    Parse a Logisim truth table file.
    Returns (input_signals, output_signals, list of row dicts).
    """
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    header_line = None
    separator_idx = None
    for i, raw in enumerate(lines):
        line = _strip_comment(raw)
        if not line:
            continue
        if "|" in line and header_line is None:
            header_line = line
            continue
        if header_line is not None and set(line.strip()).issubset(set("~")):
            separator_idx = i
            break
    if header_line is None:
        raise ValueError("Could not find header line (expected a line with '|' separating inputs and outputs)")
    if separator_idx is None:
        raise ValueError("Could not find separator line (expected a line of '~' after the header)")
    input_signals, output_signals = parse_header(header_line)
    rows = []
    for raw in lines[separator_idx + 1 :]:
        line = _strip_comment(raw)
        if not line:
            continue
        row = parse_data_line(line, input_signals, output_signals)
        if row is not None:
            rows.append(row)
    return input_signals, output_signals, rows


# --- JSON pinout ---

def load_pinout(path: Path) -> tuple[str, int, dict[int, str], float]:
    """
    Load pinout JSON. Returns (name, pin_count, pin_num_to_signal, vcc).
    pin_num_to_signal: 1-based pin number -> signal name (e.g. 1 -> "A2", 12 -> "GND").
    """
    data = json.loads(path.read_text(encoding="utf-8"))
    name = data.get("name")
    if not name:
        raise ValueError("JSON must contain 'name'")
    pins_map = data.get("pins")
    if not pins_map or not isinstance(pins_map, dict):
        raise ValueError("JSON must contain 'pins' as a map from pin number to signal name")
    pin_count = len(pins_map)
    pin_to_signal = {int(k): v for k, v in pins_map.items()}
    vcc = float(data.get("vcc", 5))
    return name, pin_count, pin_to_signal, vcc


# --- Vector building (TOML) ---

def _signal_to_toml_char(signal_name: str, value: str, is_output: bool) -> str:
    """Map signal name and value to one TOML vector character (0, 1, L, H, G, V, X)."""
    sig = signal_name.upper()
    if sig == "GND":
        return "G"
    if sig == "VCC":
        return "V"
    if sig == "NC" or signal_name == "NC":
        return "X"
    if value == "X":
        return "X"
    if is_output:
        return "H" if value == "1" else "L"
    return "1" if value == "1" else "0"


def build_vectors(
    rows: list[dict[str, str]],
    input_signals: list[str],
    output_signals: list[str],
    pin_to_signal: dict[int, str],
    pin_count: int,
) -> list[str]:
    """Build one TOML vector string per row. Each string has pin_count chars (pin 1..N in order)."""
    input_set = set(input_signals)
    output_set = set(output_signals)
    vectors = []
    for row in rows:
        vec_chars = []
        for pin_num in range(1, pin_count + 1):
            signal = pin_to_signal.get(pin_num, "NC")
            value = row.get(signal, "X")
            is_output = signal in output_set
            vec_chars.append(_signal_to_toml_char(signal, value, is_output))
        vectors.append("".join(vec_chars))
    return vectors


# --- TOML output ---

def write_toml(
    path: Path,
    name: str,
    pin_count: int,
    vcc: float,
    list_of_vector_chunks: list[list[str]],
) -> None:
    """Write xgpro-logic TOML file (one [[ics]] block per chunk, each with at most MAX_VECTORS_PER_CHUNK vectors)."""
    def esc(s: str) -> str:
        if '"' in s or "\\" in s or "\n" in s:
            return '"' + s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n") + '"'
        return f'"{s}"'
    vcc_str = str(int(vcc)) if vcc == int(vcc) else str(vcc)
    blocks = []
    for vectors in list_of_vector_chunks:
        block = [
            "[[ics]]",
            f'name = {esc(name)}',
            f"pins = {pin_count}",
            f"vcc = {vcc_str}",
            "vectors = [",
        ]
        for v in vectors:
            block.append(f"  {esc(v)},")
        block.append("]")
        blocks.append("\n".join(block))
    path.write_text("\n\n".join(blocks) + "\n", encoding="utf-8")


# --- CLI ---

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Convert Logisim truth table (.txt) + pinout (.json) to xgpro-logic TOML."
    )
    parser.add_argument("truth_table", type=Path, help="Path to Logisim truth table .txt file")
    parser.add_argument("pinout", type=Path, help="Path to pinout .json file")
    parser.add_argument("-o", "--output", type=Path, default=None, help="Output .toml path (default: truth_table name with .toml)")
    args = parser.parse_args()
    if not args.truth_table.exists():
        print(f"Error: truth table file not found: {args.truth_table}", file=sys.stderr)
        return 1
    if not args.pinout.exists():
        print(f"Error: pinout file not found: {args.pinout}", file=sys.stderr)
        return 1
    out_path = args.output
    if out_path is None:
        out_path = args.truth_table.with_suffix(".toml")
    try:
        input_signals, output_signals, rows = parse_truth_table(args.truth_table)
    except ValueError as e:
        print(f"Error parsing truth table: {e}", file=sys.stderr)
        return 1
    try:
        name, pin_count, pin_to_signal, vcc = load_pinout(args.pinout)
    except (json.JSONDecodeError, ValueError) as e:
        print(f"Error loading pinout: {e}", file=sys.stderr)
        return 1
    vectors = build_vectors(rows, input_signals, output_signals, pin_to_signal, pin_count)
    n_rows = len(vectors)
    if n_rows > MAX_VECTORS_PER_CHUNK:
        chunks = [
            vectors[i : i + MAX_VECTORS_PER_CHUNK]
            for i in range(0, len(vectors), MAX_VECTORS_PER_CHUNK)
        ]
    else:
        chunks = [vectors]
    write_toml(out_path, name, pin_count, vcc, chunks)
    if len(chunks) > 1:
        print(f"Wrote {n_rows} vectors ({len(chunks)} chunks, max {MAX_VECTORS_PER_CHUNK} per chunk) to {out_path}")
    else:
        print(f"Wrote {n_rows} vectors to {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
