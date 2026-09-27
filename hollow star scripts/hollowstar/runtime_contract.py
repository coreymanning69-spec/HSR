"""Workbench runtime-package foundation. Compile only; no live-state cutover."""
import copy
import hashlib
import json

from hollowstar import __version__ as ENGINE_VERSION
from hollowstar.content_package import validate_package
from hollowstar.generated_rules import source_for
from hollowstar.schema_contract import ContractError, validate

VERSION = "hollow-star-runtime-package-1"
COMPILER_VERSION = "1.0.0"
ID = {"type": "string", "pattern": "^[a-z][a-z0-9_-]{0,63}$"}
TEXT = {"type": "string", "minLength": 1, "maxLength": 200}
HASH = {"type": "string", "pattern": "^[a-f0-9]{64}$"}
NUMBER = {"type": "number", "minimum": 0, "maximum": 1000000}


def obj(properties, optional=()):
    return {"type": "object", "properties": properties,
            "required": [k for k in properties if k not in optional], "additionalProperties": False}


def rows(schema):
    return {"type": "array", "items": schema, "maxItems": 512}


RULE_INPUT = obj({"elapsed": NUMBER, "potency": NUMBER, "rate": NUMBER,
                  "model": {"enum": ["linear", "exponential", "logarithmic", "threshold"]},
                  "rounding": {"enum": ["floor", "ceil", "nearest"]}})
RULE_OUTPUT = obj({"potency": NUMBER})
RULE_SCHEMAS = {"status-decay-input-1": RULE_INPUT, "status-decay-output-1": RULE_OUTPUT}
BINDING = obj({"id": ID, "version": TEXT, "source_ids": rows(ID),
               "module": {"type": "string", "pattern": "^[a-z][a-z0-9_]*\\.py$"},
               "module_fingerprint": HASH,
               "input_schema": {"enum": list(RULE_SCHEMAS)},
               "output_schema": {"enum": list(RULE_SCHEMAS)},
               "capabilities": {"const": ["numeric"]},
               "timeout_ms": {"type": "integer", "minimum": 100, "maximum": 5000},
               "max_output_bytes": {"type": "integer", "minimum": 16, "maximum": 65536}})
EFFECT = obj({"id": ID, "duration": NUMBER, "potency": NUMBER, "rate": NUMBER,
              "tick_phase": {"enum": ["turn_end", "round_start", "world_tick"]},
              "decay_model": RULE_INPUT["properties"]["model"],
              "rounding": RULE_INPUT["properties"]["rounding"],
              "stack_policy": {"enum": ["replace", "refresh", "max"]},
              "immunity_tags": rows(ID), "resistance_tags": rows(ID),
              "rule_id": ID, "public_summary": TEXT})
SCHEMA = {"$schema": "https://json-schema.org/draft/2020-12/schema",
          "$id": "urn:hollow-star:runtime-package:1",
          **obj({"schema_version": {"const": VERSION}, "engine_version": {"const": ENGINE_VERSION},
                 "compiler_version": {"const": COMPILER_VERSION}, "ruleset_version": TEXT,
                 "content_fingerprint": HASH, "scene_package": {"type": "object"},
                 "actors": rows(obj({"id": ID, "entity_id": ID})),
                 "items": rows(obj({"id": ID, "entity_id": ID, "effect_ids": rows(ID)})),
                 "effects": rows(EFFECT),
                 "encounters": rows(obj({"id": ID, "scene_id": ID, "actor_ids": rows(ID),
                                          "item_ids": rows(ID), "effect_ids": rows(ID), "clock_id": ID})),
                 "clock_rules": rows(obj({"id": ID, "phase": EFFECT["properties"]["tick_phase"],
                                           "seconds": {"type": "integer", "minimum": 0, "maximum": 86400}})),
                 "state_machines": rows(obj({"id": ID, "states": rows(ID), "initial": ID,
                    "transitions": rows(obj({"from": ID, "to": ID, "event": ID}))})),
                 "assets": rows(obj({"id": ID, "asset_id": ID})),
                 "rule_bindings": rows(BINDING)})}


def fingerprint(package):
    body = {k: v for k, v in package.items() if k != "content_fingerprint"}
    return hashlib.sha256(json.dumps(body, sort_keys=True, separators=(",", ":"),
                                    ensure_ascii=True, allow_nan=False).encode()).hexdigest()


def compile_package(package, catalog=None):
    """Seal a draft and return diagnostics. Never publish, import, or execute it."""
    try:
        if not isinstance(package, dict):
            raise ContractError("runtime package must be an object")
        encoded = json.dumps(package, allow_nan=False)
        if len(encoded.encode()) > 1000000:
            raise ContractError("runtime package exceeds 1 MB")
        result = copy.deepcopy(package)
        claimed = result.get("content_fingerprint")
        actual = fingerprint(result)
        if claimed is not None and claimed != actual:
            raise ContractError("content fingerprint mismatch; remove it to compile a changed draft")
        result["content_fingerprint"] = actual
        validate(result, SCHEMA)
        scene = validate_package(result["scene_package"], catalog)
        indices = {}
        for field in ("actors", "items", "effects", "encounters", "clock_rules", "state_machines", "assets", "rule_bindings"):
            indices[field] = {row["id"]: row for row in result[field]}
            if len(indices[field]) != len(result[field]):
                raise ContractError(f"duplicate {field} IDs")
        entities = {row["id"]: row for row in result["scene_package"]["entities"]}
        scenes = {row["id"] for row in result["scene_package"]["scenes"]}
        sources = {row["id"] for row in result["scene_package"]["sources"]}

        def refs(values, known, label):
            if len(values) != len(set(values)) or any(v not in known for v in values):
                raise ContractError(f"{label}: duplicate or dangling reference")

        for field, kind in (("actors", "character"), ("items", "item")):
            for row in result[field]:
                if entities.get(row["entity_id"], {}).get("kind") != kind:
                    raise ContractError(f"{field}: missing or wrong-kind entity")
                if field == "items": refs(row["effect_ids"], indices["effects"], "item effects")
        for row in result["effects"]:
            refs([row["rule_id"]], indices["rule_bindings"], "effect rule")
            binding = indices["rule_bindings"][row["rule_id"]]
            if (binding["input_schema"], binding["output_schema"]) != ("status-decay-input-1", "status-decay-output-1"):
                raise ContractError("effect requires the status-decay rule contract")
        for row in result["rule_bindings"]:
            refs(row["source_ids"], sources, "rule sources")
            source_for(row)
        for row in result["encounters"]:
            refs([row["scene_id"]], scenes, "encounter scene")
            refs([row["clock_id"]], indices["clock_rules"], "encounter clock")
            for field in ("actor", "item", "effect"):
                refs(row[field + "_ids"], indices[field + "s"], "encounter " + field)
        from hollowstar.content_package import PRESENTATION_ASSETS
        for row in result["assets"]:
            refs([row["asset_id"]], PRESENTATION_ASSETS, "asset")
        for machine in result["state_machines"]:
            refs([machine["initial"]], machine["states"], "initial state")
            if len(machine["states"]) != len(set(machine["states"])):
                raise ContractError("duplicate states")
            seen = set()
            for transition in machine["transitions"]:
                refs([transition["from"]], machine["states"], "transition source")
                refs([transition["to"]], machine["states"], "transition target")
                key = (transition["from"], transition["event"])
                if key in seen: raise ContractError("ambiguous state transition")
                seen.add(key)
        return {"package": result, "content_fingerprint": actual, "source_verification": scene["source_verification"],
                "counts": {k: len(v) for k, v in indices.items()}, "warnings": scene["warnings"],
                "runtime_ready": False, "stage": "validated-foundation"}
    except (KeyError, TypeError, OverflowError, RecursionError) as exc:
        raise ContractError("malformed runtime package") from exc


def draft(scene_package):
    return {"schema_version": VERSION, "engine_version": ENGINE_VERSION,
            "compiler_version": COMPILER_VERSION, "ruleset_version": "hsr-generated-1",
            "scene_package": copy.deepcopy(scene_package),
            **{k: [] for k in ("actors", "items", "effects", "encounters", "state_machines",
                              "clock_rules", "assets", "rule_bindings")}}


def probe(binding, inputs):
    from hollowstar.generated_rules import invoke
    validate(binding, BINDING)
    first = invoke(binding, inputs, RULE_SCHEMAS)
    second = invoke(binding, inputs, RULE_SCHEMAS)
    if first != second:
        raise ContractError("rule outputs differ for identical inputs")
    return {"output": first, "deterministic": True, "rule_id": binding["id"],
            "module_fingerprint": binding["module_fingerprint"], "state_committed": False}
