"""Small fail-closed validator for the JSON Schema vocabulary used by HSR.

Schemas are also portable draft-2020-12 documents. Unsupported keywords are
errors rather than silently ignored constraints. No optional runtime dependency.
"""
import math
import re


class ContractError(ValueError):
    pass


def validate(value, schema, root=None, path="$"):
    root = root or schema
    supported = {"$schema", "$id", "$defs", "$ref", "title", "description", "type",
                 "properties", "required", "additionalProperties", "items", "enum", "const",
                 "minimum", "maximum", "minLength", "maxLength", "pattern", "minItems",
                 "maxItems", "uniqueItems", "anyOf"}
    if set(schema) - supported:
        raise ContractError(f"unsupported schema keywords: {sorted(set(schema) - supported)}")
    if "$ref" in schema:
        ref = schema["$ref"]
        if not ref.startswith("#/$defs/"):
            raise ContractError("only local definition references are supported")
        return validate(value, root["$defs"][ref.split("/")[-1]], root, path)
    if "anyOf" in schema:
        for option in schema["anyOf"]:
            try:
                validate(value, option, root, path)
                return
            except ContractError:
                pass
        raise ContractError(f"{path}: no matching alternative")
    kinds = {"object": isinstance(value, dict), "array": isinstance(value, list),
             "string": isinstance(value, str), "integer": type(value) is int,
             "number": type(value) in (int, float), "boolean": type(value) is bool,
             "null": value is None}
    if "type" in schema and not kinds.get(schema["type"], False):
        raise ContractError(f"{path}: expected {schema['type']}")
    if "const" in schema and value != schema["const"]:
        raise ContractError(f"{path}: unexpected constant")
    if "enum" in schema and value not in schema["enum"]:
        raise ContractError(f"{path}: unsupported value {value!r}")
    if type(value) in (int, float):
        if not math.isfinite(value):
            raise ContractError(f"{path}: non-finite number")
        if value < schema.get("minimum", -math.inf) or value > schema.get("maximum", math.inf):
            raise ContractError(f"{path}: number outside bounds")
    if isinstance(value, str):
        if not schema.get("minLength", 0) <= len(value) <= schema.get("maxLength", 1000000):
            raise ContractError(f"{path}: text outside bounds")
        if "pattern" in schema and not re.search(schema["pattern"], value):
            raise ContractError(f"{path}: pattern mismatch")
    if isinstance(value, dict):
        if set(schema.get("required", [])) - value.keys():
            raise ContractError(f"{path}: missing required fields")
        properties = schema.get("properties", {})
        if schema.get("additionalProperties") is False and value.keys() - properties.keys():
            raise ContractError(f"{path}: unexpected fields {sorted(value.keys() - properties.keys())}")
        for key, child in value.items():
            if key in properties:
                validate(child, properties[key], root, f"{path}.{key}")
    if isinstance(value, list):
        if not schema.get("minItems", 0) <= len(value) <= schema.get("maxItems", 100000):
            raise ContractError(f"{path}: array outside bounds")
        if schema.get("uniqueItems") and any(v in value[:i] for i, v in enumerate(value)):
            raise ContractError(f"{path}: duplicate values")
        for i, child in enumerate(value):
            if "items" in schema:
                validate(child, schema["items"], root, f"{path}[{i}]")
