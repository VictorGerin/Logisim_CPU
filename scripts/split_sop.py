#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Split a sum-of-products equation into multiple outputs for GAL22V10 pin limits.

Used when one output has more product terms than a single OLMC allows.
Parts are _Y0, _Y1, ... (intermediate); the final output Y gets a direct term
chunk plus OR of the intermediates: Y = (direct terms) + _Y0 + _Y1 + ...

As a module:
  from split_sop import parse_equation_rhs, split_sop_to_blocks
  terms = parse_equation_rhs("Y = A + B + C")
  blocks = split_sop_to_blocks(equation_block, parts_config, output_name="Y")
"""

from __future__ import annotations

import re


class InsufficientTermsError(Exception):
    """Raised when the number of product terms is less than the split capacity."""

    def __init__(self, output_name: str, have: int, need: int):
        self.output_name = output_name
        self.have = have
        self.need = need
        missing = need - have
        super().__init__(
            f"Termos insuficientes: a variável {output_name!r} não conseguiu ser completada. "
            f"Faltam {missing} termos (possui {have}, necessita {need})."
        )


class ExcessTermsError(Exception):
    """Raised when the number of product terms exceeds the split capacity."""

    def __init__(self, output_name: str, have: int, capacity: int):
        self.output_name = output_name
        self.have = have
        self.capacity = capacity
        excess = have - capacity
        super().__init__(
            f"Termos em excesso: a variável {output_name!r} não conseguiu ser completada. "
            f"Excedem {excess} termos (possui {have}, capacidade do output_splits {capacity})."
        )


def parse_equation_rhs(equation_block: str) -> tuple[str, list[str]]:
    """
    Parse an equation block "OutName = T1 + T2 + ..." into (lhs_name, list of terms).

    Terms are product expressions (may contain * and spaces). The RHS is split
    on " + " (plus surrounded by whitespace, including newlines).
    """
    eq = equation_block.strip()
    if " = " not in eq:
        return "", []
    lhs, rhs = eq.split(" = ", 1)
    lhs = lhs.strip()
    # Split RHS on one or more " + " (whitespace-plus-whitespace)
    raw_terms = re.split(r"\s+\+\s+", rhs)
    terms = [t.strip() for t in raw_terms if t.strip()]
    return lhs, terms


def split_sop_to_blocks(
    equation_block: str,
    parts: list[dict],
    output_name: str,
    emit_tristate_gnd: bool = False,
) -> list[str]:
    """
    Split one equation block into multiple blocks for parts and final output.

    Intermediate parts are emitted as combinatorial outputs (no .E = GND), so
    the GAL22V10 feedback (from the pin) reflects the computed value for use in Y.

    Args:
        equation_block: Single block "OutName = T1 + T2 + ...".
        parts: List of part configs from output_splits[output_name], each with
               "label", "max_terms"; last entry is the final pin (same as output_name).
        output_name: Name of the output being split (e.g. "Y").
        emit_tristate_gnd: Unused (kept for compatibility). No longer used: .E = GND
            would break internal feedback on GAL22V10 (feedback is from the pin).

    Returns:
        List of equation blocks (strings), order: _Y0, _Y1, ..., Y = ...
    """
    lhs, terms = parse_equation_rhs(equation_block)
    if lhs != output_name:
        return [equation_block]
    if not parts:
        return [equation_block]

    total_capacity = sum(int(p.get("max_terms", 0)) for p in parts)
    n_terms = len(terms)
    if n_terms > total_capacity:
        raise ExcessTermsError(output_name, n_terms, total_capacity)

    blocks: list[str] = []
    idx = 0
    part_labels: list[str] = []

    for i, part in enumerate(parts):
        label = part["label"]
        max_terms = int(part.get("max_terms", 0))
        chunk = terms[idx : idx + max_terms]
        idx += max_terms

        indent = " " * len(f"{output_name} = ")

        if label == output_name:
            # Final pin: Y = (direct terms) + _Y0 + _Y1 + ...
            rhs_parts = []
            if chunk:
                rhs_parts.append((" +\n" + indent).join(chunk))
            if part_labels:
                rhs_parts.append((" +\n" + indent).join(part_labels))
            rhs = (" +\n" + indent).join(rhs_parts)
            prefix = f"{output_name} = "
            blocks.append(prefix + rhs)
        else:
            # Intermediate part: combinatorial output (no .E = GND) so feedback is valid
            part_labels.append(label)
            prefix = f"{label} = "
            indent_part = " " * len(prefix)
            if not chunk:
                eq_rhs = "0"
            else:
                eq_rhs = (" +\n" + indent_part).join(chunk)
            blocks.append(prefix + eq_rhs)

    return blocks


def apply_output_splits(
    equation_blocks: list[str],
    output_labels: list[str],
    output_splits: dict,
    emit_tristate_gnd: bool = False,
) -> list[str]:
    """
    Apply output_splits config to equation_blocks; return new list of blocks.

    output_splits is the "output_splits" object from JSON, e.g. {"Y": [{"pin": 15, "label": "_Y0", "max_terms": 8}, ...]}.
    Blocks for outputs not in output_splits are left unchanged. Order of outputs
    follows output_labels; within a split, order is parts then final.
    """
    if not output_splits:
        return list(equation_blocks)

    result: list[str] = []
    out_idx = 0
    for out_name in output_labels:
        if out_idx >= len(equation_blocks):
            break
        block = equation_blocks[out_idx]
        out_idx += 1

        if out_name not in output_splits:
            result.append(block)
            continue

        parts = output_splits[out_name]
        if not isinstance(parts, list) or not parts:
            result.append(block)
            continue

        split_blocks = split_sop_to_blocks(
            block, parts, output_name=out_name, emit_tristate_gnd=emit_tristate_gnd
        )
        result.extend(split_blocks)

    # Append any remaining blocks (shouldn't happen if len(output_labels) == len(equation_blocks))
    while out_idx < len(equation_blocks):
        result.append(equation_blocks[out_idx])
        out_idx += 1

    return result
