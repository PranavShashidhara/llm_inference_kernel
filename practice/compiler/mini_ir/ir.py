"""A tiny SSA IR for practice. Straight-line code only (one block).

Text format:

    func @f(%a, %b) {
      %c = const 4
      %0 = add %a, %c
      print %0
      ret %0
    }

Ops: const (attr), add, sub, mul (2 operands), print (side effect), ret.
Every value is defined exactly once (SSA).
"""
from __future__ import annotations
from dataclasses import dataclass, field
import re

PURE_OPS = {"const", "add", "sub", "mul"}
SIDE_EFFECT_OPS = {"print", "ret"}
COMMUTATIVE = {"add", "mul"}


@dataclass
class Op:
    opcode: str
    operands: list[str] = field(default_factory=list)
    result: str | None = None      # e.g. "%0"; None for print/ret
    attr: int | None = None        # only used by const

    def __str__(self):
        if self.opcode == "const":
            rhs = f"const {self.attr}"
        else:
            rhs = f"{self.opcode} " + ", ".join(self.operands)
        return f"{self.result} = {rhs}" if self.result else rhs


@dataclass
class Function:
    name: str
    args: list[str]
    ops: list[Op]

    def __str__(self):
        body = "\n".join(f"  {op}" for op in self.ops)
        return f"func @{self.name}({', '.join(self.args)}) {{\n{body}\n}}"


def parse(text: str) -> Function:
    lines = [l.strip() for l in text.strip().splitlines() if l.strip()]
    m = re.match(r"func @(\w+)\((.*)\) \{", lines[0])
    assert m, f"bad header: {lines[0]}"
    args = [a.strip() for a in m.group(2).split(",") if a.strip()]
    ops, defined = [], set(args)
    for line in lines[1:]:
        if line == "}":
            break
        res = None
        if "=" in line:
            res, line = [s.strip() for s in line.split("=")]
            assert res not in defined, f"SSA violation: {res} defined twice"
            defined.add(res)
        opcode, *rest = line.split(None, 1)
        if opcode == "const":
            ops.append(Op("const", [], res, int(rest[0])))
        else:
            operands = [s.strip() for s in rest[0].split(",")] if rest else []
            for o in operands:
                assert o in defined, f"{o} used before definition"
            ops.append(Op(opcode, operands, res))
    return Function(m.group(1), args, ops)


def dump(fn: Function) -> str:
    return str(fn)


def run(fn: Function, args: list[int]) -> tuple[int | None, list[int]]:
    """Interpret fn. Returns (return_value, printed_values).
    Use it to check that an optimization did not change behavior."""
    env = dict(zip(fn.args, args))
    printed, ret = [], None
    for op in fn.ops:
        if op.opcode == "const":
            env[op.result] = op.attr
        elif op.opcode in ("add", "sub", "mul"):
            a, b = (env[o] for o in op.operands)
            env[op.result] = {"add": a + b, "sub": a - b, "mul": a * b}[op.opcode]
        elif op.opcode == "print":
            printed.append(env[op.operands[0]])
        elif op.opcode == "ret":
            ret = env[op.operands[0]]
    return ret, printed


def replace_all_uses(fn: Function, old: str, new: str) -> None:
    """Rewrite every operand `old` into `new`. (MLIR: replaceAllUsesWith)"""
    for op in fn.ops:
        op.operands = [new if o == old else o for o in op.operands]
