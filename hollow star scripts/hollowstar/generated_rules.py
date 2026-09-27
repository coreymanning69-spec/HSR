"""Bounded Python-subset rule interpreter, executed in an isolated subprocess.

Never eval/exec/import generated code. Only JSON values and explicit arithmetic
operations exist in this language; Python objects, attributes and I/O do not.
"""
import ast
import hashlib
import json
import math
import operator
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parent / "generated"
FUNCTIONS = {"min": min, "max": max, "abs": abs, "round": round,
             "floor": math.floor, "ceil": math.ceil, "log1p": math.log1p,
             "exp": math.exp, "sqrt": math.sqrt}
BINARY = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
          ast.Div: operator.truediv, ast.FloorDiv: operator.floordiv,
          ast.Mod: operator.mod}
COMPARE = {ast.Eq: operator.eq, ast.NotEq: operator.ne, ast.Lt: operator.lt,
           ast.LtE: operator.le, ast.Gt: operator.gt, ast.GtE: operator.ge}


class RuleError(ValueError):
    pass


def parse(source):
    if not isinstance(source, str) or len(source.encode()) > 32768:
        raise RuleError("rule source limit is 32 KiB")
    try:
        tree = ast.parse(source)
    except (SyntaxError, RecursionError) as exc:
        raise RuleError("invalid rule syntax") from exc
    if len(tree.body) != 1 or not isinstance(tree.body[0], ast.FunctionDef):
        raise RuleError("rule must contain only def resolve(inputs)")
    fn = tree.body[0]
    if (fn.name != "resolve" or [a.arg for a in fn.args.args] != ["inputs"]
            or fn.decorator_list or fn.args.defaults or fn.args.kwonlyargs
            or fn.args.posonlyargs or fn.args.vararg or fn.args.kwarg or fn.returns):
        raise RuleError("rule signature must be resolve(inputs)")
    allowed = (ast.Module, ast.FunctionDef, ast.arguments, ast.arg, ast.Return,
               ast.Assign, ast.If, ast.IfExp, ast.Expr, ast.Constant, ast.Name,
               ast.Load, ast.Store, ast.Subscript, ast.Dict, ast.List, ast.BinOp,
               ast.UnaryOp, ast.USub, ast.UAdd, ast.Not, ast.Call, ast.Compare,
               ast.BoolOp, ast.And, ast.Or, *BINARY, *COMPARE)
    nodes = list(ast.walk(tree))
    if len(nodes) > 2000:
        raise RuleError("rule AST exceeds budget")
    for node in nodes:
        if not isinstance(node, allowed):
            raise RuleError(f"forbidden syntax: {type(node).__name__}")
        if isinstance(node, ast.FunctionDef) and node is not fn:
            raise RuleError("nested functions are forbidden")
        if isinstance(node, ast.Name) and node.id.startswith("_"):
            raise RuleError("private identifiers are forbidden")
        if isinstance(node, ast.Call) and (not isinstance(node.func, ast.Name)
                or node.func.id not in FUNCTIONS or node.keywords):
            raise RuleError("only explicit numeric functions are callable")
        if isinstance(node, ast.Assign) and (len(node.targets) != 1 or not isinstance(node.targets[0], ast.Name)):
            raise RuleError("only local variable assignments are supported")
        if isinstance(node, ast.Dict) and any(k is None for k in node.keys):
            raise RuleError("dictionary unpacking is forbidden")
    return fn


def evaluate(source, inputs):
    fn = parse(source)
    env = {"inputs": inputs}
    budget = [4096]

    def bounded(value):
        if type(value) in (int, float) and (not math.isfinite(value) or abs(value) > 1e12):
            raise RuleError("numeric rule limit exceeded")
        if isinstance(value, (str, list, dict)) and len(value) > 4096:
            raise RuleError("value size limit exceeded")
        return value

    def expr(n):
        budget[0] -= 1
        if budget[0] < 0:
            raise RuleError("rule operation budget exhausted")
        if isinstance(n, ast.Constant): return bounded(n.value)
        if isinstance(n, ast.Name): return env[n.id]
        if isinstance(n, ast.Subscript): return bounded(expr(n.value)[expr(n.slice)])
        if isinstance(n, ast.Dict): return {expr(k): expr(v) for k, v in zip(n.keys, n.values)}
        if isinstance(n, ast.List): return [expr(v) for v in n.elts]
        if isinstance(n, ast.BinOp):
            a, b = expr(n.left), expr(n.right)
            if type(a) not in (int, float) or type(b) not in (int, float):
                raise RuleError("arithmetic requires numbers")
            return bounded(BINARY[type(n.op)](a, b))
        if isinstance(n, ast.UnaryOp):
            v = expr(n.operand)
            return bounded(not v if isinstance(n.op, ast.Not) else -v if isinstance(n.op, ast.USub) else +v)
        if isinstance(n, ast.Call): return bounded(FUNCTIONS[n.func.id](*[expr(a) for a in n.args]))
        if isinstance(n, ast.IfExp): return expr(n.body if expr(n.test) else n.orelse)
        if isinstance(n, ast.BoolOp):
            return all(bool(expr(v)) for v in n.values) if isinstance(n.op, ast.And) else any(bool(expr(v)) for v in n.values)
        if isinstance(n, ast.Compare):
            a = expr(n.left)
            for op, right in zip(n.ops, n.comparators):
                b = expr(right)
                if not COMPARE[type(op)](a, b): return False
                a = b
            return True
        raise RuleError("unsupported expression")

    def block(nodes):
        for n in nodes:
            if isinstance(n, ast.Return): return True, expr(n.value)
            if isinstance(n, ast.Assign): env[n.targets[0].id] = expr(n.value)
            elif isinstance(n, ast.If):
                returned, value = block(n.body if expr(n.test) else n.orelse)
                if returned: return True, value
            elif isinstance(n, ast.Expr): expr(n.value)
        return False, None
    returned, result = block(fn.body)
    if not returned or not isinstance(result, dict):
        raise RuleError("rule must return an object")
    return result


def source_for(binding):
    path = ROOT / binding["module"]
    if path.suffix != ".py" or path.resolve().parent != ROOT.resolve() or path.is_symlink():
        raise RuleError("rule module must be a direct generated namespace member")
    source = path.read_text(encoding="utf-8")
    if hashlib.sha256(path.read_bytes()).hexdigest() != binding["module_fingerprint"]:
        raise RuleError("generated module fingerprint mismatch")
    parse(source)
    return source


def invoke(binding, inputs, schemas):
    from hollowstar.schema_contract import validate
    validate(inputs, schemas[binding["input_schema"]])
    source = source_for(binding)
    request = json.dumps({"source": source, "inputs": inputs}, allow_nan=False).encode()
    if len(request) > 65536:
        raise RuleError("rule request exceeds 64 KiB")
    try:
        result = subprocess.run([sys.executable, "-I", "-B", str(Path(__file__).resolve()), "--worker"],
            input=request, capture_output=True, timeout=binding["timeout_ms"] / 1000,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    except subprocess.TimeoutExpired as exc:
        raise RuleError("generated rule timed out; no state committed") from exc
    if result.returncode or len(result.stdout) > binding["max_output_bytes"]:
        raise RuleError("generated rule failed or exceeded output limit")
    try:
        payload = json.loads(result.stdout)
        validate(payload, schemas[binding["output_schema"]])
        return payload
    except (ValueError, KeyError) as exc:
        raise RuleError("invalid generated rule output") from exc


if __name__ == "__main__":
    try:
        req = json.loads(sys.stdin.buffer.read(65537))
        result = evaluate(req["source"], req["inputs"])
        encoded = json.dumps(result, allow_nan=False, sort_keys=True)
        if len(encoded.encode()) > 65536:
            raise RuleError("worker output limit exceeded")
        print(encoded)
    except Exception:
        raise SystemExit(2)
