"""A small, safe arithmetic evaluator for the agent's `calculate` tool (no eval/exec)."""

from __future__ import annotations

import ast
import math
import operator

_BINOPS = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
           ast.Div: operator.truediv, ast.Pow: operator.pow, ast.Mod: operator.mod}
_UNARY = {ast.UAdd: operator.pos, ast.USub: operator.neg}
_FUNCS = {"ln": math.log, "log": math.log, "log10": math.log10, "exp": math.exp, "sqrt": math.sqrt,
          "abs": abs, "min": min, "max": max, "sum": lambda *a: sum(a), "round": round}
_CONSTS = {"pi": math.pi, "e": math.e}


class CalcError(ValueError):
    pass


def _eval(node):
    if isinstance(node, ast.Expression):
        return _eval(node.body)
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in _BINOPS:
        left, right = _eval(node.left), _eval(node.right)
        if isinstance(node.op, ast.Pow) and abs(right) > 1000:
            raise CalcError("exponent too large")
        return _BINOPS[type(node.op)](left, right)
    if isinstance(node, ast.UnaryOp) and type(node.op) in _UNARY:
        return _UNARY[type(node.op)](_eval(node.operand))
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in _FUNCS:
        if node.keywords:
            raise CalcError("keyword arguments are not supported")
        return _FUNCS[node.func.id](*[_eval(a) for a in node.args])
    if isinstance(node, ast.Name) and node.id in _CONSTS:
        return _CONSTS[node.id]
    if isinstance(node, (ast.List, ast.Tuple)):
        raise CalcError("lists are not supported; pass numbers as separate arguments")
    raise CalcError(f"unsupported expression element: {ast.dump(node)[:60]}")


def calculate(expression: str) -> float:
    expr = expression.replace("^", "**").replace("×", "*").strip()
    if len(expr) > 2000:
        raise CalcError("expression too long")
    try:
        tree = ast.parse(expr, mode="eval")
    except SyntaxError as exc:
        raise CalcError(f"syntax error: {exc.msg}") from None
    try:
        value = _eval(tree)
    except (ZeroDivisionError, OverflowError, ValueError, TypeError) as exc:
        raise CalcError(str(exc)) from None
    return float(value)
