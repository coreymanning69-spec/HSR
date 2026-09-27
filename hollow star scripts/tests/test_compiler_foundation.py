import copy
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from hollowstar.generated_rules import ROOT, RuleError, evaluate, invoke, parse
from hollowstar.runtime_contract import compile_package, draft, probe, RULE_SCHEMAS
from hollowstar.host import HSRHost
import hsr_mcp_server

HSR = Path(__file__).resolve().parents[1]


def binding():
    return {"id": "decay", "version": "1.0.0", "source_ids": [], "module": "decay.py",
            "module_fingerprint": hashlib.sha256((ROOT / "decay.py").read_bytes()).hexdigest(),
            "input_schema": "status-decay-input-1", "output_schema": "status-decay-output-1",
            "capabilities": ["numeric"], "timeout_ms": 2000, "max_output_bytes": 1024}


def inputs(model="linear"):
    return {"elapsed": 2, "potency": 10, "rate": 1, "model": model, "rounding": "floor"}


class FoundationTests(unittest.TestCase):
    def setUp(self):
        self.package = draft(json.loads((HSR / "web/content-package-example.json").read_text(encoding="utf-8")))
        self.package["rule_bindings"] = [binding()]

    def test_compile_hash_is_reproducible_and_tampering_rejected(self):
        first = compile_package(self.package)
        self.assertEqual(first, compile_package(first["package"]))
        self.assertFalse(first["runtime_ready"])
        changed = copy.deepcopy(first["package"])
        changed["ruleset_version"] = "changed"
        with self.assertRaisesRegex(ValueError, "fingerprint"):
            compile_package(changed)

    def test_invalid_shapes_references_and_nonfinite_numbers(self):
        changes = [lambda p: p.update(unexpected=True),
                   lambda p: p["rule_bindings"].append(binding()),
                   lambda p: p["rule_bindings"][0].update(module="../host.py"),
                   lambda p: p["rule_bindings"][0].update(module_fingerprint="0" * 64),
                   lambda p: p.update(assets=[{"id": "fake", "asset_id": "missing"}]),
                   lambda p: p.update(clock_rules=[{"id": "clock", "phase": "world_tick", "seconds": float("nan")}]),
                   lambda p: p.update(state_machines=[{"id": "door", "states": ["closed"], "initial": "closed",
                                                       "transitions": [{"from": "closed", "to": "missing", "event": "open"}]}])]
        for change in changes:
            p = copy.deepcopy(self.package)
            change(p)
            with self.subTest(package=p), self.assertRaises(ValueError): compile_package(p)
        with self.assertRaises(ValueError): compile_package(None)

    def test_all_decay_models_in_real_worker(self):
        for model, expected in (("linear", 8), ("exponential", 1), ("logarithmic", 8), ("threshold", 0)):
            with self.subTest(model=model):
                receipt = probe(binding(), inputs(model))
                self.assertEqual(receipt["output"]["potency"], expected)
                self.assertFalse(receipt["state_committed"])

    def test_rule_language_cannot_access_python_objects_or_io(self):
        for body in ("import os\nreturn {}", "return inputs.__class__", "return open('x')",
                     "return __import__('os')", "while True:\n    pass", "return {'x': 2 ** 100000}"):
            with self.subTest(body=body), self.assertRaises(ValueError):
                parse("def resolve(inputs):\n    " + body.replace("\n", "\n    ") + "\n")
        with self.assertRaises(RuleError): evaluate("def resolve(inputs):\n    return {'x': 'a' * 1000000}\n", {})

    def test_worker_failure_timeout_and_bad_output_fail_closed(self):
        with patch("hollowstar.generated_rules.subprocess.run", side_effect=subprocess.TimeoutExpired("worker", 1)):
            with self.assertRaisesRegex(RuleError, "timed out"): invoke(binding(), inputs(), RULE_SCHEMAS)
        for code, payload in ((2, b""), (0, b"not json"), (0, b'{"potency": -1}'), (0, b'x' * 2048)):
            with patch("hollowstar.generated_rules.subprocess.run", return_value=subprocess.CompletedProcess([], code, payload)):
                with self.assertRaises(RuleError): invoke(binding(), inputs(), RULE_SCHEMAS)

    def test_host_and_mcp_use_existing_authoring_surface(self):
        with tempfile.TemporaryDirectory() as temp:
            host = HSRHost.from_options(HSR.parent, data_root=Path(temp) / ".local")
            for command, fields in (("packet_runtime_schema", {}), ("packet_compile", {"package": self.package}),
                                    ("packet_rule_validate", {"binding": binding()}),
                                    ("packet_rule_probe", {"binding": binding(), "inputs": inputs()})):
                response = host.handle({"id": command, "command": command, **fields})
                self.assertTrue(response["ok"], response)
            bad = host.handle({"id": "bad", "command": "packet_compile", "package": None})
            self.assertEqual(bad["error"]["code"], "CONTENT_INVALID")
            self.assertFalse(host.booted)
            self.assertFalse((Path(temp) / ".local/reliquary_runs").exists())
        for name in ("hsr_compile_package", "hsr_runtime_schema", "hsr_validate_rule", "hsr_probe_rule"):
            self.assertIn(name, hsr_mcp_server.TOOLS_BY_NAME)

    def test_reusable_hooks_and_saved_run_probe_do_not_mutate(self):
        from hollowstar.runtime_hooks import load_package, evaluate_effect
        from hollowstar.run_service import RunService, RunServiceError
        from hollowstar.run_state import save_run
        from hollowstar.combat import Encounter
        from hollowstar.actors import Actor, Provenance
        from hollowstar.rng import RunRNG
        from hollowstar.clock import SCHEMA as CLOCK_SCHEMA
        self.package["effects"] = [{"id": "frost", "duration": 10, "potency": 10, "rate": 1,
            "tick_phase": "turn_end", "decay_model": "linear", "rounding": "floor",
            "stack_policy": "refresh", "immunity_tags": [], "resistance_tags": [],
            "rule_id": "decay", "public_summary": "Frost weakens."}]
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            package_file = root / "package.json"
            package_file.write_text(json.dumps(self.package), encoding="utf-8")
            sealed = load_package(package_file, workspace_root=HSR.parent)
            self.assertEqual(evaluate_effect(sealed, "frost", elapsed=2)["output"], {"potency": 8})
            service = RunService(root / ".local/reliquary_runs")
            run = Encounter([Actor("Tester", provenance=Provenance(snapshot_version="test"))],
                            [Actor("Target")], RunRNG("probe"))
            run.context["dungeon"] = {"event_clock": {"schema": CLOCK_SCHEMA, "turn": 7, "round": 2, "seconds": 42}}
            path = save_run(run, "probe", service._path_for("probe"), snapshot_version="test")
            before = path.read_bytes()
            result = service.probe_package_effect("probe", sealed, "frost", since=5)
            self.assertEqual(result["output"], {"potency": 8})
            self.assertEqual(result["clock_counter"], "turn")
            self.assertFalse(service._active)
            self.assertEqual(path.read_bytes(), before)
            service._active["probe"] = run
            state_before = copy.deepcopy(run.context)
            rng_before = run.rng.getstate()
            host = HSRHost.from_options(HSR.parent, data_root=root / ".local")
            host._run_service = service
            for command, fields in (("packet_effect_probe", {"elapsed": 2}),
                                    ("packet_run_effect_probe", {"run_id": "probe", "since": 5})):
                reply = host.handle({"id": command, "command": command, "package": sealed,
                                     "effect_id": "frost", **fields})
                self.assertTrue(reply["ok"], reply)
                self.assertEqual(reply["result"]["output"], {"potency": 8})
            for since in (-1, 8, True):
                with self.assertRaises(RunServiceError): service.probe_package_effect("probe", sealed, "frost", since=since)
            reply = host.handle({"id": "invalid-probe", "command": "packet_run_effect_probe",
                                 "package": sealed, "effect_id": "frost", "run_id": "probe", "since": 8})
            self.assertFalse(reply["ok"], reply)
            with self.assertRaises(ValueError): evaluate_effect(sealed, "missing", elapsed=1)
            self.assertEqual(run.context, state_before)
            self.assertEqual(run.rng.getstate(), rng_before)
            self.assertEqual(path.read_bytes(), before)
            run.context.clear()
            with self.assertRaisesRegex(RunServiceError, "event clock"):
                service.probe_package_effect("probe", sealed, "frost")
        for name in ("hsr_probe_effect", "hsr_probe_run_effect"):
            self.assertIn(name, hsr_mcp_server.TOOLS_BY_NAME)


if __name__ == "__main__":
    unittest.main()
