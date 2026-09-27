"""Reusable compiler hooks. Receipts are diagnostic; callers never mutate runs."""
import json
from pathlib import Path

from hollowstar.runtime_contract import compile_package, probe
from hollowstar.schema_contract import ContractError
from hollowstar.source_catalog import SourceCatalog


def load_package(path, *, workspace_root):
    """Read and validate a draft or sealed JSON package, verifying live sources."""
    source = Path(path)
    with source.open("rb") as stream:
        raw = stream.read(1_000_001)
    if len(raw) > 1_000_000:
        raise ContractError("runtime package exceeds 1 MB")
    return compile_package(json.loads(raw), SourceCatalog(Path(workspace_root)))["package"]


def evaluate_effect(package, effect_id, *, elapsed, catalog=None):
    """Probe initial potency decay at elapsed phase units, without applying it.

    Immunity, resistance, stacking and duration expiry require host application
    policy and deliberately are not simulated by this mathematical hook.
    """
    compiled = compile_package(package, catalog)
    package = compiled["package"]
    effect = next((row for row in package["effects"] if row["id"] == effect_id), None)
    if effect is None:
        raise ContractError("unknown effect ID")
    binding = next(row for row in package["rule_bindings"] if row["id"] == effect["rule_id"])
    inputs = {"elapsed": elapsed, "potency": effect["potency"], "rate": effect["rate"],
              "model": effect["decay_model"], "rounding": effect["rounding"]}
    return {**probe(binding, inputs), "effect_id": effect_id, "elapsed": elapsed,
            "tick_phase": effect["tick_phase"], "content_fingerprint": compiled["content_fingerprint"],
            "source_verification": compiled["source_verification"],
            "scope": "potency-formula-only", "public_summary": effect["public_summary"]}
