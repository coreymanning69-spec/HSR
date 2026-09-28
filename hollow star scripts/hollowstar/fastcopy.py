"""Fast deep copy for the engine's JSON-shaped runtime state.

``copy.deepcopy`` is general: every node pays for a type dispatch table,
``__deepcopy__``/``__reduce_ex__`` probing and keep-alive bookkeeping. Almost
all of a run's transactional state is plain ``dict``/``list``/scalars, so this
copier walks those directly and hands anything else (Actors, Items, dataclasses,
dict subclasses, ...) to ``copy.deepcopy`` with the *same* memo.

Semantics match ``copy.deepcopy`` for what callers can observe:
  * objects pre-seeded in ``memo`` (shared, immutable payloads) are reused;
  * aliasing is preserved -- a container reached twice is copied once;
  * exact ``dict``/``list``/``set`` types only; subclasses take the slow path.

Originals are not added to the memo's keep-alive list: every source container
stays reachable from the object being copied for the whole call, so its id
cannot be recycled mid-copy (the fallback path keeps its own temporaries alive).
"""
from __future__ import annotations

import copy

_ATOMIC = frozenset({type(None), bool, int, float, complex, str, bytes, range, type})


def fast_deepcopy(value, memo: dict | None = None):
    if memo is None:
        memo = {}
    return _copy(value, memo)


def _copy(value, memo):
    cls = type(value)
    if cls in _ATOMIC:
        return value
    key = id(value)
    found = memo.get(key, memo)
    if found is not memo:
        return found
    if cls is dict:
        out = {}
        memo[key] = out
        for k, v in value.items():
            out[k if type(k) in _ATOMIC else _copy(k, memo)] = (
                v if type(v) in _ATOMIC else _copy(v, memo))
        return out
    if cls is list:
        out = []
        memo[key] = out
        out.extend([v if type(v) in _ATOMIC else _copy(v, memo) for v in value])
        return out
    if cls is tuple:
        items = [v if type(v) in _ATOMIC else _copy(v, memo) for v in value]
        # A self-referencing tuple may have been built while copying its items.
        found = memo.get(key, memo)
        if found is not memo:
            return found
        out = value if all(a is b for a, b in zip(items, value)) else tuple(items)
        memo[key] = out
        return out
    if cls is set or cls is frozenset:
        out = cls(v if type(v) in _ATOMIC else _copy(v, memo) for v in value)
        memo[key] = out
        return out
    return copy.deepcopy(value, memo)

