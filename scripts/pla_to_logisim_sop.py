#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Convert a minimized PLA (from truth_table_to_pla.py / Espresso) into a
Logisim-evolution .circ file implementing the Sum of Products (SOP) circuit
using discrete AND, OR, and NOT gates.

Each product term becomes an AND gate binary tree (or a direct wire for
single-literal terms).  Each output bit gets an OR gate binary tree collecting
all terms that drive it.  Signals are routed via Logisim Tunnel components to
avoid wire-crossing issues that would arise from a physical bus layout.

Layout (left to right):
  Col A: Input pins + NOT gates, with labelled source tunnels for each signal.
  Col B: AND gate trees (one per active product term), stacked vertically.
  Col C: OR gate trees (one per output bit) + output pins.

Usage:
  python scripts/pla_to_logisim_sop.py INPUT.pla --out-circ circuit.circ
  python scripts/truth_table_to_pla.py tt.txt | \\
      python scripts/pla_to_logisim_sop.py - --out-circ circuit.circ
"""

from __future__ import annotations

import argparse
import math
import re
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path


# ─── PlaData ──────────────────────────────────────────────────────────────────

@dataclass
class PlaData:
    input_labels: list[str]
    output_labels: list[str]
    terms: list[tuple[str, str]]

    @classmethod
    def parse(cls, lines: list[str]) -> "PlaData":
        """
        Parse a PLA file (full PLA with headers, or data-lines-only output from
        truth_table_to_pla.py).
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

        if n_inputs is None:
            n_inputs = len(terms[0][0])
        if n_outputs is None:
            n_outputs = len(terms[0][1])
        if input_labels is None:
            input_labels = [f"in{i}" for i in range(n_inputs)]
        if output_labels is None:
            output_labels = [f"out{i}" for i in range(n_outputs)]

        for inp, out in terms:
            if len(inp) != n_inputs:
                raise ValueError(
                    f"Input pattern width {len(inp)} ≠ {n_inputs}: {inp!r}"
                )
            if len(out) != n_outputs:
                raise ValueError(
                    f"Output pattern width {len(out)} ≠ {n_outputs}: {out!r}"
                )

        return cls(input_labels, output_labels, terms)

    @property
    def active_terms(self) -> list[tuple[str, str]]:
        terms: list[tuple[str, str]] = []
        for inp, out in self.terms:
            for m, bit in enumerate(out):
                if bit == "1":
                    single = "0" * m + "1" + "0" * (len(out) - m - 1)
                    terms.append((inp, single))
        return sorted(terms, key=lambda t: t[1].index("1"))


# ─── Group detection ──────────────────────────────────────────────────────────

def _detect_groups(
    labels: list[str],
) -> list[str | tuple[str, list[str]]]:
    """
    Detect enumerated labels and group them.

    Returns an ordered list where each element is either:
      - str                        → individual label
      - (prefix, [lbl0..lblN-1])  → group of N bits (sorted by numeric suffix)

    Groups are only formed when a prefix has ALL indices 0..N-1 present.
    """
    parsed: list[tuple[str, int] | None] = []
    for lbl in labels:
        m = re.match(r'^(.*?)(\d+)$', lbl)
        parsed.append((m.group(1), int(m.group(2))) if m else None)

    groups: dict[str, list[tuple[int, str]]] = defaultdict(list)
    for lbl, p in zip(labels, parsed):
        if p:
            groups[p[0]].append((p[1], lbl))

    valid_groups: dict[str, list[str]] = {}
    for prefix, items in groups.items():
        items.sort()
        if prefix and [idx for idx, _ in items] == list(range(len(items))):
            valid_groups[prefix] = [lbl for _, lbl in items]

    result: list[str | tuple[str, list[str]]] = []
    seen: set[str] = set()
    for lbl in labels:
        if lbl in seen:
            continue
        m = re.match(r'^(.*?)(\d+)$', lbl)
        if m and m.group(1) in valid_groups:
            prefix = m.group(1)
            result.append((prefix, valid_groups[prefix]))
            seen.update(valid_groups[prefix])
        else:
            result.append(lbl)
            seen.add(lbl)
    return result


# ─── Layout ───────────────────────────────────────────────────────────────────

class Layout:
    """
    Coordenadas e parâmetros de geometria para posicionar todos os componentes
    no canvas do Logisim-evolution (eixo X cresce para a direita, Y para baixo).

    Visão geral das três colunas do circuito:

      ┌─────────── COL A ──────────────┐  ┌──── COL B ────┐  ┌──── COL C ─────┐
      │  Pinos + inversores + tunnels  │  │  Árvores AND  │  │  Árvores OR +  │
      │  para sinal positivo/negado    │  │  por produto  │  │  pinos de saída│
      └────────────────────────────────┘  └───────────────┘  └────────────────┘
    """

    # ─── Col A: Pinos de entrada e inversores ─────────────────────────────────
    #
    #  X_PIN_IN  X_TUN_POS        X_NOT_OUT  X_TUN_NEG
    #     50        130              200        250
    #     │          │                │          │
    #  ──[>]──wire──►[T "sig"]──wire─►[NOT]──wire►[T "sig_n"]
    #                          ←──────────────►
    #                             NOT_DEPTH=20
    #                      (entrada do NOT está 20 px
    #                       à esquerda do seu output)
    #
    X_PIN_IN   = 100    # X do output port do componente Pin de entrada
    X_SPLIT_IN = 130    # X do bus do Splitter de entrada (para grupos de bits)
    X_TUN_POS  = 160   # X do tunnel-fonte do sinal positivo  (label = "sig")
    X_NOT_OUT  = 200   # X do output port do gate NOT
    X_TUN_NEG  = 250   # X do tunnel-fonte do sinal negado    (label = "sig_n")

    # ─── Col B: Árvores de gates AND (uma por produto ativo) ──────────────────
    #
    #  X_AND  X_TUN_AND
    #   550      570
    #    │         │
    #  [AND]──wire►[T "_tj"]   ← tunnel que leva o produto j para a Col C
    #
    X_AND     = 550   # X do output port da raiz da árvore AND de cada produto
    X_TUN_AND = 570   # X do tunnel que exporta o sinal do produto para a Col C

    # ─── Espaçamento vertical (eixo Y, cresce para baixo) ─────────────────────
    #
    #  Y_PIN_START = 100  ──  in0 [>]
    #                    ↕  Y_PIN_STEP = 70
    #                170  ──  in1 [>]
    #                    ↕  Y_PIN_STEP = 70
    #                240  ──  in2 [>]  ...
    #
    #  AND_MIN_STEP: espaço mínimo (px) entre os centros Y de árvores AND
    #  consecutivas. Pode ser aumentado automaticamente para árvores largas.
    #
    Y_PIN_START   = 100  # Y do primeiro pino de entrada
    Y_PIN_STEP    = 70   # Distância vertical entre pinos de entrada consecutivos
    AND_MIN_STEP  = 50   # Passo mínimo entre os centros Y de dois produtos AND
    SPLIT_SPACING = 7    # Y_PIN_STEP / 10 → bits do Splitter espaçados 70 px

    # ─── Col C: Splitter de saída (grupos enumerados) ─────────────────────────
    #
    #  x_pin_out  x_pin_out+X_SPLIT_OUT_OFFSET  (Splitter bus)  x_mp
    #      │               │                                      │
    #   [T src] ······· [T rcv]──wire──►[SPL west]──wire──►[Pin multi-bit]
    #                                    ←── 20 ──►
    #                         ←── 50 ───►
    #                ←────── X_SPLIT_OUT_OFFSET ──►
    #
    X_SPLIT_OUT_OFFSET = 400  # distância de x_pin_out ao bus do Splitter de saída

    # ─── Parâmetros dos gates ──────────────────────────────────────────────────
    #
    #  NOT_SIZE  → atributo Logisim <a name="size" val="20"/> no NOT Gate
    #  NOT_DEPTH → profundidade do NOT: a porta de entrada fica em
    #              x = X_NOT_OUT − NOT_DEPTH  (20 px à esquerda do output)
    #  GATE_SIZE → atributo Logisim <a name="size" val="50"/> nos AND/OR Gates
    #
    NOT_SIZE  = 20   # Tamanho do gate NOT  (pixels lógicos do Logisim)
    NOT_DEPTH = 20   # Distância entre o output do NOT e sua porta de entrada
    GATE_SIZE = 50   # Tamanho dos gates AND/OR (pixels lógicos do Logisim)

    # ─── Geometria interna das árvores binárias (AND / OR) ────────────────────
    #
    #  Cada gate de 2 entradas (facing east) tem o seguinte diagrama de portas:
    #
    #   (x_out − GATE_DEPTH,  y_out − GATE_PORT_OFFSET) ──┐
    #                                                      [GATE]── (x_out, y_out)
    #   (x_out − GATE_DEPTH,  y_out + GATE_PORT_OFFSET) ──┘
    #   ←──────────────────────────────────────────────────►
    #                      GATE_DEPTH = 50
    #
    #  Quando uma folha é um literal único, o tunnel receptor é colocado
    #  LEAF_TUN_OFFSET px antes do output da raiz e ligado por wire até a porta:
    #
    #   (x_out − LEAF_TUN_OFFSET, y_port) ──wire──► (x_out − GATE_DEPTH, y_port)
    #   ←──────────────────────────────────────────►
    #                  LEAF_TUN_OFFSET = 80
    #
    #  Para sub-árvores com mais de um literal, cada nível é recuado
    #  TREE_X_STEP px à esquerda, e os centroides Y são calculados
    #  usando TREE_LEAF_SPACING como espaçamento entre folhas:
    #
    #   nível 0 (raiz)    nível 1              folhas (tunnels)
    #     x_out        x_out − TREE_X_STEP   x_out − LEAF_TUN_OFFSET
    #       │                  │                      │
    #     [AND] ─────────── [AND] ────────── [T "a"]
    #                    \─ [AND] ────────── [T "b"]
    #                               \─────── [T "c"]
    #
    GATE_DEPTH        = 50   # Distância horizontal: output do gate → suas portas de entrada
    GATE_PORT_OFFSET  = 20   # Deslocamento vertical ± de cada porta de entrada
    TREE_X_STEP       = 70   # Recuo horizontal entre níveis consecutivos da árvore
    TREE_LEAF_SPACING = 40   # Espaçamento entre folhas para calcular centroides Y
    LEAF_TUN_OFFSET   = 80   # Distância da raiz até o tunnel de um literal individual


# ─── Xml ──────────────────────────────────────────────────────────────────────

class Xml:
    HEADER = """\
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

    FOOTER = """\
  </circuit>
</project>
"""

    @staticmethod
    def _esc(val: str) -> str:
        return (
            val.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
        )

    @staticmethod
    def _loc(x: int, y: int) -> str:
        return f"({x},{y})"

    @classmethod
    def _comp(cls, lib: int, x: int, y: int, name: str,
              attrs: dict[str, str] | None = None) -> str:
        parts = [f'  <comp lib="{lib}" loc="{cls._loc(x, y)}" name="{cls._esc(name)}">']
        for k, v in (attrs or {}).items():
            parts.append(f'    <a name="{cls._esc(k)}" val="{cls._esc(v)}"/>')
        parts.append("  </comp>")
        return "\n".join(parts)

    @classmethod
    def wire(cls, x1: int, y1: int, x2: int, y2: int) -> str:
        return f'  <wire from="{cls._loc(x1, y1)}" to="{cls._loc(x2, y2)}"/>'

    @classmethod
    def tunnel(cls, x: int, y: int, label: str, facing: str = "east") -> str:
        return cls._comp(0, x, y, "Tunnel", {"facing": facing, "label": label})

    @classmethod
    def pin_in(cls, x: int, y: int, label: str, width: int = 1) -> str:
        attrs: dict[str, str] = {"appearance": "classic", "label": label}
        if width > 1:
            attrs["width"] = str(width)
        return cls._comp(0, x, y, "Pin", attrs)

    @classmethod
    def pin_out(cls, x: int, y: int, label: str, width: int = 1) -> str:
        attrs: dict[str, str] = {
            "appearance": "classic",
            "facing": "west",
            "label": label,
            "type": "output",
        }
        if width > 1:
            attrs["width"] = str(width)
        return cls._comp(0, x, y, "Pin", attrs)

    @classmethod
    def splitter(cls, x: int, y: int, fanout: int,
                 facing: str | None = None, spacing: int = 1,
                 bit_map: list[int] | None = None) -> str:
        attrs: dict[str, str] = {"fanout": str(fanout), "incoming": str(fanout)}
        if facing:
            attrs["facing"] = facing
        if spacing != 1:
            attrs["spacing"] = str(spacing)
        if bit_map is not None:
            for i, v in enumerate(bit_map):
                attrs[f"bit{i}"] = str(v)
        return cls._comp(0, x, y, "Splitter", attrs)

    @classmethod
    def not_gate(cls, x: int, y: int) -> str:
        return cls._comp(1, x, y, "NOT Gate", {"size": str(Layout.NOT_SIZE)})

    @classmethod
    def and_gate(cls, x: int, y: int) -> str:
        """2-input AND gate (no inputs= attribute)."""
        return cls._comp(1, x, y, "AND Gate", {"size": str(Layout.GATE_SIZE)})

    @classmethod
    def or_gate(cls, x: int, y: int) -> str:
        """2-input OR gate (no inputs= attribute)."""
        return cls._comp(1, x, y, "OR Gate", {"size": str(Layout.GATE_SIZE)})

    @classmethod
    def constant(cls, x: int, y: int, value: int) -> str:
        return cls._comp(0, x, y, "Constant", {"value": hex(value)})


# ─── GateTree ─────────────────────────────────────────────────────────────────

class GateTree:
    """
    Build a balanced binary tree of 2-input gates whose output lands at
    (x_out, y_out).

    Gate geometry (size=30, facing east):
      Output port     : (x_out, y_out)
      Top input port  : (x_out - GATE_DEPTH,  y_out - GATE_PORT_OFFSET)
      Bottom input port: (x_out - GATE_DEPTH, y_out + GATE_PORT_OFFSET)
      Tunnel for top  : (x_out - LEAF_TUN_OFFSET, y_out - GATE_PORT_OFFSET) ──wire──► port
      Tunnel for bottom: (x_out - LEAF_TUN_OFFSET, y_out + GATE_PORT_OFFSET) ──wire──► port

    Z-shape routing from sub-gate output (x_g, y_g) to parent port (x_p, y_p):
      if y_g == y_p : single horizontal wire
      else          : three wires via x_mid = (x_g + x_p) // 2
    """

    @classmethod
    def build(cls, elems: list[str], gate_fn, lits: list[str],
              x_out: int, y_out: int) -> None:
        """
        Emit XML elements for a balanced gate tree.

        gate_fn(x, y) -> str : Xml.and_gate or Xml.or_gate
        lits                  : ordered list of signal label strings
        Output signal appears at (x_out, y_out).
        """
        K = len(lits)

        if K == 0:
            # Always-true constant; wire feeds the output position.
            elems.append(Xml.constant(x_out - Layout.GATE_DEPTH, y_out, 1))
            elems.append(Xml.wire(x_out - Layout.GATE_DEPTH, y_out, x_out, y_out))

        elif K == 1:
            # Single literal: receive tunnel placed at the output position.
            elems.append(Xml.tunnel(x_out, y_out, lits[0], "west"))

        else:
            # Balanced split: root gate + two sub-trees.
            elems.append(gate_fn(x_out, y_out))
            half = K // 2

            # Y positions of K leaves centred at y_out, spacing = TREE_LEAF_SPACING.
            leaf_ys = [
                y_out + round((i - (K - 1) / 2) * Layout.TREE_LEAF_SPACING)
                for i in range(K)
            ]
            left_lits  = lits[:half]
            right_lits = lits[half:]
            y_left  = sum(leaf_ys[:half])  // half
            y_right = sum(leaf_ys[half:])  // (K - half)

            px        = x_out - Layout.GATE_DEPTH         # x_out - 30
            top_port_y = y_out - Layout.GATE_PORT_OFFSET  # y_out - 10
            bot_port_y = y_out + Layout.GATE_PORT_OFFSET  # y_out + 10

            # ── Left (top) sub-group ──────────────────────────────────────────
            if len(left_lits) == 1:
                # Single leaf: tunnel directly adjacent to the parent's input port.
                elems.append(Xml.tunnel(x_out - Layout.LEAF_TUN_OFFSET, top_port_y, left_lits[0], "east"))
                elems.append(Xml.wire(x_out - Layout.LEAF_TUN_OFFSET, top_port_y, px, top_port_y))
            else:
                x_sub = x_out - Layout.TREE_X_STEP
                cls.build(elems, gate_fn, left_lits, x_sub, y_left)
                cls._z_route(elems, x_sub, y_left, px, top_port_y)

            # ── Right (bottom) sub-group ──────────────────────────────────────
            if len(right_lits) == 1:
                elems.append(Xml.tunnel(x_out - Layout.LEAF_TUN_OFFSET, bot_port_y, right_lits[0], "east"))
                elems.append(Xml.wire(x_out - Layout.LEAF_TUN_OFFSET, bot_port_y, px, bot_port_y))
            else:
                x_sub = x_out - Layout.TREE_X_STEP
                cls.build(elems, gate_fn, right_lits, x_sub, y_right)
                cls._z_route(elems, x_sub, y_right, px, bot_port_y)

    @staticmethod
    def _z_route(elems: list[str], x_g: int, y_g: int, x_p: int, y_p: int) -> None:
        """Route from sub-gate output (x_g, y_g) to parent input port (x_p, y_p)."""
        if y_g == y_p:
            elems.append(Xml.wire(x_g, y_g, x_p, y_p))
        else:
            x_mid = (x_g + x_p) // 2
            elems.append(Xml.wire(x_g, y_g, x_mid, y_g))
            elems.append(Xml.wire(x_mid, y_g, x_mid, y_p))
            elems.append(Xml.wire(x_mid, y_p, x_p, y_p))


# ─── SopBuilder ───────────────────────────────────────────────────────────────

class SopBuilder:
    """Build the full Logisim-evolution .circ XML for the SOP circuit."""

    def __init__(self, pla: PlaData, circuit_name: str = "sop") -> None:
        self._pla = pla
        self._circuit_name = circuit_name
        self._elems: list[str] = []

    def build(self) -> str:
        """Entry point — returns the complete .circ XML string."""
        active_terms = self._pla.active_terms
        self._build_col_a()
        and_y, y_and_start = self._compute_and_layout(active_terms)
        term_tun = self._build_col_b(active_terms, and_y)
        self._build_col_c(active_terms, and_y, term_tun, y_and_start)
        body = "\n".join(self._elems)
        return Xml.HEADER.format(name=self._circuit_name) + body + "\n" + Xml.FOOTER

    # ── Col A ─────────────────────────────────────────────────────────────────

    def _build_col_a(self) -> None:
        """Input pins, NOT gates, and source tunnels for positive/negated signals."""
        Lo = Layout
        y = Lo.Y_PIN_START

        def _signal_row(label: str, y_row: int, x_start: int) -> None:
            """Emit wire + pos tunnel + NOT + neg tunnel for one signal bit."""
            self._elems.append(Xml.wire(x_start, y_row, Lo.X_TUN_POS, y_row))
            self._elems.append(Xml.wire(Lo.X_TUN_POS, y_row, Lo.X_TUN_POS, y_row - 30))
            self._elems.append(Xml.wire(Lo.X_TUN_POS, y_row - 30, Lo.X_TUN_POS - 10, y_row - 30))
            self._elems.append(Xml.tunnel(Lo.X_TUN_POS - 10, y_row - 30, label, "east"))
            self._elems.append(Xml.wire(Lo.X_TUN_POS, y_row, Lo.X_NOT_OUT - Lo.NOT_DEPTH, y_row))
            self._elems.append(Xml.not_gate(Lo.X_NOT_OUT, y_row))
            self._elems.append(Xml.wire(Lo.X_NOT_OUT, y_row, Lo.X_TUN_NEG, y_row))
            self._elems.append(Xml.tunnel(Lo.X_TUN_NEG, y_row, f"{label}_n", "west"))

        for item in _detect_groups(self._pla.input_labels):
            if isinstance(item, str):
                # Individual 1-bit input
                label = item
                self._elems.append(Xml.pin_in(Lo.X_PIN_IN, y, label))
                _signal_row(label, y, Lo.X_PIN_IN)
                y += Lo.Y_PIN_STEP
            else:
                # Grouped input: multi-bit pin + east-facing Splitter
                prefix, group_labels = item
                N = len(group_labels)
                y_first = y
                # Signal rows in reverse order (MSB at top, LSB at bottom)
                # Splitter east-facing: bit i at (X_SPLIT_IN+20, y_bus - 70*(i+1))
                # reversed order maps: j=0 → ctrlN-1 (MSB) at y_first + 0
                #                      j=N-1 → ctrl0 (LSB) at y_first + (N-1)*70
                # which matches bit N-1..0 from top to bottom ✓
                for j, lbl in enumerate(reversed(group_labels)):
                    y_row = y_first + j * Lo.Y_PIN_STEP
                    _signal_row(lbl, y_row, Lo.X_SPLIT_IN + 20)
                # Bus row below the signal rows.
                # Logisim east-facing Splitter: bit i at (loc.x+20, loc.y - 10 - i*70).
                # To align bit 0 at y_first+(N-1)*70 we need loc.y = y_first+N*70 - 60.
                y_bus = y_first + N * Lo.Y_PIN_STEP   # pin_in row
                y_spl = y_bus - 60                     # Splitter bus loc
                self._elems.append(Xml.pin_in(Lo.X_PIN_IN, y_bus, prefix, width=N))
                self._elems.append(Xml.wire(Lo.X_PIN_IN, y_bus, Lo.X_SPLIT_IN, y_bus))
                self._elems.append(Xml.wire(Lo.X_SPLIT_IN, y_bus, Lo.X_SPLIT_IN, y_spl))
                self._elems.append(Xml.splitter(
                    Lo.X_SPLIT_IN, y_spl, N,
                    spacing=Lo.SPLIT_SPACING,
                    bit_map=[N - 1 - i for i in range(N)],
                ))
                y = y_bus + Lo.Y_PIN_STEP

    # ── Layout helpers ────────────────────────────────────────────────────────

    def _compute_and_layout(
        self, active_terms: list[tuple[str, str]]
    ) -> tuple[list[int], int]:
        """Return (and_y list, y_and_start) for the AND tree rows."""
        Lo = Layout
        k_max = max(
            (sum(1 for c in inp if c in "01") for inp, _ in active_terms),
            default=1,
        )
        and_step = max(k_max * Lo.TREE_LEAF_SPACING, Lo.AND_MIN_STEP)
        y_and_start = Lo.Y_PIN_START
        and_y = [y_and_start + j * and_step for j in range(len(active_terms))]
        return and_y, y_and_start

    # ── Col B ─────────────────────────────────────────────────────────────────

    def _build_col_b(
        self, active_terms: list[tuple[str, str]], and_y: list[int]
    ) -> list[str]:
        """AND gate trees, one per active product term. Returns term tunnel labels."""
        Lo = Layout
        term_tun: list[str] = []
        for j, (inp, _out) in enumerate(active_terms):
            y_and = and_y[j]
            lits = [
                self._pla.input_labels[k] if c == "1"
                else f"{self._pla.input_labels[k]}_n"
                for k, c in enumerate(inp) if c in "01"
            ]
            tun = f"_t{j}"
            GateTree.build(self._elems, Xml.and_gate, lits, Lo.X_AND, y_and)
            self._elems.append(Xml.wire(Lo.X_AND, y_and, Lo.X_TUN_AND, y_and))
            self._elems.append(Xml.tunnel(Lo.X_TUN_AND, y_and, tun, "west"))
            term_tun.append(tun)
        return term_tun

    # ── Col C ─────────────────────────────────────────────────────────────────

    def _build_col_c(
        self,
        active_terms: list[tuple[str, str]],
        and_y: list[int],
        term_tun: list[str],
        y_and_start: int,
    ) -> None:
        """OR gate trees and output pins, one per output label."""
        Lo = Layout
        M = len(self._pla.output_labels)

        # Compute X_OR based on the largest AND tree width + 100 padding.
        k_max = max(
            (sum(1 for c in inp if c in "01") for inp, _ in active_terms),
            default=1,
        )
        and_tree_w = (math.ceil(math.log2(k_max)) - 1) * Lo.TREE_X_STEP + Lo.LEAF_TUN_OFFSET if k_max >= 2 else 0
        x_or      = Lo.X_TUN_AND + and_tree_w + 360
        x_pin_out = x_or + 30

        # Which terms contribute to each output bit?
        contributing: list[list[int]] = []
        for m in range(M):
            contrib = [
                j for j, (_, out) in enumerate(active_terms)
                if m < len(out) and out[m] == "1"
            ]
            contributing.append(contrib)

        # Centre each OR tree on the mean Y of its contributing AND rows.
        or_y: list[int] = []
        used_y: set[int] = set()
        for m in range(M):
            contrib = contributing[m]
            if contrib and active_terms:
                cy = sum(and_y[j] for j in contrib) // len(contrib)
            else:
                cy = y_and_start + m * Lo.AND_MIN_STEP
            if cy in used_y:
                for step in range(10, 100_000, 10):
                    if cy + step not in used_y:
                        cy = cy + step
                        break
                    if cy - step not in used_y:
                        cy = cy - step
                        break
            used_y.add(cy)
            or_y.append(cy)

        # Emit OR trees and output pins (grouped-aware).
        label_to_m = {lbl: m for m, lbl in enumerate(self._pla.output_labels)}

        for item in _detect_groups(self._pla.output_labels):
            if isinstance(item, str):
                # Individual 1-bit output
                m = label_to_m[item]
                y_or = or_y[m]
                contrib = contributing[m]
                if not contrib:
                    self._elems.append(Xml.constant(x_or - Lo.LEAF_TUN_OFFSET, y_or, 0))
                    self._elems.append(Xml.wire(x_or - Lo.LEAF_TUN_OFFSET, y_or, x_pin_out, y_or))
                    self._elems.append(Xml.pin_out(x_pin_out, y_or, item))
                else:
                    GateTree.build(self._elems, Xml.or_gate, [term_tun[j] for j in contrib], x_or, y_or)
                    self._elems.append(Xml.wire(x_or, y_or, x_pin_out, y_or))
                    self._elems.append(Xml.pin_out(x_pin_out, y_or, item))
            else:
                # Grouped output: OR outputs → named tunnels → west-facing Splitter
                # → multi-bit output pin.
                #
                # Logisim west-facing Splitter at (x_spl, y_spl):
                #   bus port  : (x_spl,      y_spl)
                #   bit i port: (x_spl - 20, y_spl + 10 + i*70)   [spacing=7]
                prefix, group_labels = item
                N = len(group_labels)
                group_indices = [label_to_m[lbl] for lbl in group_labels]

                x_spl = x_pin_out + Lo.X_SPLIT_OUT_OFFSET   # Splitter loc X
                x_rcv = x_spl - 50                           # receiver tunnel X
                x_mp  = x_spl + 30                           # multi-bit output pin X

                # Align Splitter so bit 0 lands at min(or_y) of the group.
                y_spl = min(or_y[m] for m in group_indices) - 10

                # OR tree (or constant) → wire → source tunnel (west-facing)
                for i, m in enumerate(group_indices):
                    y_or_m    = or_y[m]
                    contrib   = contributing[m]
                    tun_label = f"_go_{group_labels[i]}"
                    if not contrib:
                        self._elems.append(Xml.constant(x_or - Lo.LEAF_TUN_OFFSET, y_or_m, 0))
                        self._elems.append(Xml.wire(x_or - Lo.LEAF_TUN_OFFSET, y_or_m, x_pin_out, y_or_m))
                    else:
                        GateTree.build(self._elems, Xml.or_gate,
                                       [term_tun[j] for j in contrib], x_or, y_or_m)
                        self._elems.append(Xml.wire(x_or, y_or_m, x_pin_out, y_or_m))
                    self._elems.append(Xml.tunnel(x_pin_out, y_or_m, tun_label, "west"))

                # Splitter + multi-bit output pin
                self._elems.append(Xml.splitter(x_spl, y_spl, N,
                                                facing="west", spacing=Lo.SPLIT_SPACING))
                self._elems.append(Xml.wire(x_spl, y_spl, x_mp, y_spl))
                self._elems.append(Xml.pin_out(x_mp, y_spl, prefix, width=N))

                # Receiver tunnels (east-facing) wired to each Splitter bit port
                for i, lbl in enumerate(group_labels):
                    tun_label = f"_go_{lbl}"
                    y_bit = y_spl + 10 + i * Lo.Y_PIN_STEP
                    self._elems.append(Xml.tunnel(x_rcv, y_bit, tun_label, "east"))
                    self._elems.append(Xml.wire(x_rcv, y_bit, x_spl - 20, y_bit))


# ─── CLI entry point ───────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Convert a minimized PLA to a Logisim-evolution SOP circuit (.circ). "
            "Each product term becomes an AND gate tree; each output gets an OR gate tree."
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
        pla = PlaData.parse(lines)
    except ValueError as e:
        print(f"Error parsing PLA: {e}", file=sys.stderr)
        return 1

    active = pla.active_terms
    print(
        f"Inputs: {len(pla.input_labels)}  Outputs: {len(pla.output_labels)}  "
        f"Terms: {len(pla.terms)} ({len(active)} with active outputs)",
        file=sys.stderr,
    )

    # Generate circuit XML
    circ_xml = SopBuilder(pla, args.circuit_name).build()

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
