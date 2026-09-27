"""Compiler boundary, provenance, isolation, and persistence acceptance tests."""
from __future__ import annotations

import copy
import hashlib
import json
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from pathlib import Path

from hollowstar.content_package import PackageError, public_view, initial_state, source_starter, validate_package
from hollowstar.content_preview import PreviewConflict, PreviewStore
from hollowstar.host import CONTENT_COMMANDS, HSRHost
from hollowstar.hosted_controls import HostedControls
from hollowstar.markdown_interpreter import interpret_markdown
from hollowstar.source_catalog import SourceCatalog, SourceError

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "web/content-package-example.json"


class ContentWorkbenchTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.corpus = self.root / "divine mythos set"
        self.corpus.mkdir()
        self.source = self.corpus / "sample.md"
        self.source.write_text("---\nid: SAMPLE\n---\n# Crossing\nA bridge.\n## M12\nA quiet archive.\n", encoding="utf-8")
        self.catalog = SourceCatalog(self.root)
        self.package = json.loads(EXAMPLE.read_text(encoding="utf-8"))
        self.db = self.root / ".local/content_workbench/previews.sqlite3"
        self.store = PreviewStore(self.db)

    def test_catalog_searches_nested_sources_and_excludes_disposable_content(self):
        for folder in ("source extracts/chapter", ".local", "project context/_snapshots/old", "hollow star scripts/node_modules/pkg"):
            target = self.root / folder
            target.mkdir(parents=True)
            (target / "reference.md").write_text("A quiet archive.", encoding="utf-8")
        result = self.catalog.search("quiet archive")
        self.assertEqual(result["total"], 2)
        self.assertEqual(result["sources"][0]["classification"], "canonical-source")
        self.assertEqual(result["sources"][0]["line"], 7)
        self.assertTrue(result["read_only"])
        self.assertFalse(self.db.exists())

    def test_archive_read_is_explicit_and_classified(self):
        archive = self.root / "project context/_history"
        archive.mkdir(parents=True)
        (archive / "reference.md").write_text("history", encoding="utf-8")
        self.assertEqual(self.catalog.search("history")["total"], 0)
        result = self.catalog.search("history", include_archives=True)
        self.assertEqual(result["sources"][0]["classification"], "archive")
        with self.assertRaises(SourceError):
            self.catalog.read("project context/_history/reference.md")

    def test_source_paths_and_ranges_fail_closed(self):
        for path in ("../sample.md", "C:/private/sample.md", "/sample.md", ".local/secret.json", "x/../../sample.md", "bad\x00.md", "bad\ud800.md"):
            with self.subTest(path=path), self.assertRaises((SourceError, OSError)):
                self.catalog.read(path)
        for params in ({"start_line": 0}, {"start_line": True}, {"line_count": 401}, {"line_count": -1}, {"start_line": 99}):
            with self.subTest(params=params), self.assertRaises(SourceError):
                self.catalog.read("divine mythos set/sample.md", **params)

    def test_symlink_is_never_a_source(self):
        target = self.root / "linked.md"
        try:
            target.symlink_to(self.source)
        except OSError:
            self.skipTest("host does not grant symlink creation")
        with self.assertRaises(SourceError):
            self.catalog.read("linked.md")

    def test_asset_inventory_does_not_parse_binary_as_text(self):
        (self.root / "map.pdf").write_bytes(b"%PDF-fake")
        result = self.catalog.search("map.pdf")["sources"][0]
        self.assertFalse(result["text_readable"])
        with self.assertRaises(SourceError):
            self.catalog.read("map.pdf")

    def test_starter_preserves_exact_excerpt_and_verifiable_provenance(self):
        before = self.source.read_bytes()
        source = self.catalog.read("divine mythos set/sample.md", start_line=4, line_count=2)
        package = source_starter(source)
        report = validate_package(package, self.catalog)
        self.assertEqual(report["source_verification"], "verified")
        self.assertEqual(package["scenes"][0]["description"], "# Crossing\nA bridge.")
        self.assertEqual(package["sources"][0]["sha256"], hashlib.sha256(before).hexdigest())
        self.assertEqual(package["entities"], [])
        self.assertEqual(self.source.read_bytes(), before)

    def test_interpreter_drafts_explicit_structure_and_preserves_ambiguous_prose(self):
        self.source.write_text('---\ntitle: "Archive Walk"\nverse: Mergeverse\n---\n# Crossing\nA bridge at dusk.\nCharacter: Guide — Carries a map.\nInteraction: Guide | Ask for map | The guide shows the map.\n## Archive\nAn uncertain omen.\nInteraction: Stranger | Ask | No answer.\n', encoding='utf-8')
        receipt = self.catalog.read('divine mythos set/sample.md')
        draft = interpret_markdown(receipt)
        report = validate_package(draft['package'], self.catalog)
        self.assertEqual(report['source_verification'], 'verified')
        self.assertEqual(draft['package']['universe'], 'Mergeverse')
        self.assertEqual(len(draft['package']['scenes']), 2)
        self.assertEqual(draft['package']['entities'][0]['name'], 'Guide')
        self.assertEqual(draft['package']['entities'][0]['interactions'][0]['text'], 'The guide shows the map.')
        self.assertIn('An uncertain omen.', draft['package']['scenes'][1]['description'])
        self.assertIn('Interaction: Stranger', draft['package']['scenes'][1]['description'])
        self.assertTrue(draft['review_flags'])
        self.source.write_text('Changed\n', encoding='utf-8')
        with self.assertRaisesRegex(PackageError, 'source changed'):
            validate_package(draft['package'], self.catalog)

    def test_interpreter_requires_markdown_and_respects_package_limits(self):
        receipt = self.catalog.read('divine mythos set/sample.md')
        with self.assertRaises(PackageError):
            interpret_markdown({**receipt, 'path': 'sample.txt'})
        self.source.write_text('# Long\n' + 'x' * 12001, encoding='utf-8')
        with self.assertRaisesRegex(PackageError, 'scene description limit'):
            interpret_markdown(self.catalog.read('divine mythos set/sample.md'))

    def test_stale_source_and_out_of_bounds_reference_are_rejected(self):
        package = source_starter(self.catalog.read("divine mythos set/sample.md"))
        invalid = copy.deepcopy(package)
        invalid["sources"][0]["end_line"] = 99
        with self.assertRaises(PackageError):
            validate_package(invalid, self.catalog)
        self.source.write_text("Changed\n", encoding="utf-8")
        with self.assertRaisesRegex(PackageError, "source changed"):
            validate_package(package, self.catalog)

    def test_graph_and_field_validation_rejects_unsupported_packages(self):
        for change in (
            lambda p: p.update(schema_version="future"),
            lambda p: p.update(code="print('no')"),
            lambda p: p["scenes"][0]["exits"][0].update(target="missing"),
            lambda p: p["scenes"][0].update(exits=[]),
            lambda p: p["scenes"][0].update(entities=["missing"]),
            lambda p: p["entities"][0].update(damage=100),
            lambda p: p["entities"].append(copy.deepcopy(p["entities"][0])),
            lambda p: p["scenes"][0].update(description="x" * 12001),
        ):
            candidate = copy.deepcopy(self.package)
            change(candidate)
            with self.subTest(candidate=candidate["id"]), self.assertRaises(PackageError):
                validate_package(candidate)

    def test_public_view_has_no_hidden_or_unvisited_content(self):
        hidden = {"id": "hidden", "name": "Secret character", "kind": "character", "description": "SECRET VALUE", "visibility": "hidden", "source_ids": []}
        self.package["entities"].append(hidden)
        self.package["scenes"][0]["entities"].append("hidden")
        view = self.store.start(self.package, "start")
        encoded = json.dumps(view)
        self.assertNotIn("Secret character", encoded)
        self.assertNotIn("SECRET VALUE", encoded)
        self.assertNotIn("Blank Folio", encoded)
        self.assertNotIn("source_ids", encoded)
        self.assertNotIn("payload", encoded)
        with self.assertRaises(PackageError):
            self.store.act(view["preview_id"], {"type": "inspect", "target": "hidden"}, 0, "invalid")
        self.assertEqual(self.store.read(view["preview_id"])["revision"], 0)

    def test_two_previews_are_independent_and_resume_in_a_fresh_service(self):
        first = self.store.start(self.package, "start-one")
        second = self.store.start(self.package, "start-two")
        reached = self.store.act(first["preview_id"], {"type": "navigate", "target": "archive"}, 0, "move")
        self.assertEqual(reached["scene"]["id"], "archive")
        fresh = PreviewStore(self.db)
        self.assertEqual(fresh.read(first["preview_id"]), reached)
        self.assertEqual(fresh.read(second["preview_id"])["scene"]["id"], "crossing")
        self.assertFalse((self.root / ".local/reliquary_runs").exists())

    def test_retry_is_idempotent_and_operation_identity_cannot_be_reused(self):
        view = self.store.start(self.package, "start")
        self.assertEqual(self.store.start(self.package, "start"), view)
        action = {"type": "inspect", "target": "lantern"}
        first = self.store.act(view["preview_id"], action, 0, "inspect")
        self.assertEqual(self.store.act(view["preview_id"], action, 0, "inspect"), first)
        self.assertEqual(self.store.read(view["preview_id"])["revision"], 1)
        with self.assertRaises(PreviewConflict):
            self.store.act(view["preview_id"], {"type": "navigate", "target": "archive"}, 0, "inspect")
        changed = copy.deepcopy(self.package)
        changed["title"] = "Changed"
        with self.assertRaises(PreviewConflict):
            self.store.start(changed, "start")

    def test_simultaneous_writers_cannot_silently_overwrite_each_other(self):
        view = self.store.start(self.package, "start")
        def act(number):
            try:
                return PreviewStore(self.db).act(view["preview_id"], {"type": "inspect", "target": "guide"}, 0, f"op-{number}")
            except PreviewConflict:
                return "conflict"
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(act, (1, 2)))
        self.assertEqual(results.count("conflict"), 1)
        self.assertEqual(self.store.read(view["preview_id"])["revision"], 1)

    def test_separate_python_processes_share_the_revision_boundary(self):
        view = self.store.start(self.package, "process-start")
        script = """import json,sys
from pathlib import Path
from hollowstar.content_preview import PreviewStore, PreviewConflict
try:
    result=PreviewStore(Path(sys.argv[1])).act(sys.argv[2], {"type":"inspect","target":"guide"}, 0, sys.argv[3])
    print(json.dumps({"revision":result["revision"]}))
except PreviewConflict:
    print(json.dumps({"conflict":True}))
"""
        def worker(index):
            result = subprocess.run([sys.executable, "-c", script, str(self.db), view["preview_id"], f"worker-{index}"],
                                    cwd=ROOT, capture_output=True, text=True, encoding="utf-8", timeout=20)
            self.assertEqual(result.returncode, 0, result.stderr)
            return json.loads(result.stdout)
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(worker, (1, 2)))
        self.assertEqual(sum(row.get("conflict", False) for row in results), 1)
        self.assertEqual(self.store.read(view["preview_id"])["revision"], 1)

    def test_real_divineverse_and_mergeverse_packets_are_locally_accessible(self):
        catalog = SourceCatalog(ROOT.parent)
        corpus = ROOT.parent / "divine mythos set"
        for pattern, universe in (("*_T_STY_*.md", "Divineverse"), ("*_M_STY_*.md", "Mergeverse")):
            source = sorted(corpus.glob(pattern))[0]
            relative = source.relative_to(ROOT.parent).as_posix()
            before = source.read_bytes()
            excerpt = catalog.read(relative, start_line=1, line_count=12)
            package = source_starter(excerpt, universe=universe)
            report = validate_package(package, catalog)
            self.assertEqual(report["source_verification"], "verified")
            view = self.store.start(package, universe.lower())
            self.assertEqual(view["package"]["universe"], universe)
            self.assertEqual(view["scene"]["description"], excerpt["text"])
            self.assertEqual(source.read_bytes(), before)

    def test_invalid_actions_do_not_mutate_state_and_packages_stay_immutable(self):
        view = self.store.start(self.package, "start")
        self.package["scenes"][0]["title"] = "Not the stored package"
        for action in ({"type": "attack", "target": "guide"}, {"type": "inspect", "target": "folio"}, {"type": "navigate", "target": "unknown"}):
            with self.assertRaises(PackageError):
                self.store.act(view["preview_id"], action, 0, "invalid")
            self.assertEqual(self.store.read(view["preview_id"]), view)
        self.assertEqual(self.store.export(view["preview_id"])["scenes"][0]["title"], "The Unwritten Crossing")

    def test_interaction_is_validated_and_receipt_survives_reload(self):
        view = self.store.start(self.package, "start")
        result = self.store.act(view["preview_id"], {"type": "interact", "target": "guide", "interaction_id": "map"}, 0, "talk")
        self.assertIn("Two places", result["last_event"]["text"])
        self.assertEqual(PreviewStore(self.db).read(view["preview_id"]), result)

    def test_asset_references_are_registered_and_not_arbitrary_urls(self):
        from hollowstar.content_package import PRESENTATION_ASSETS
        view = self.store.start(self.package, "art")
        guide = next(e for e in view["entities"] if e["id"] == "guide")
        self.assertEqual(guide["art"]["src"], "/assets/townsperson.png")
        schema = json.loads((ROOT / "web/content-package.schema.json").read_text(encoding="utf-8"))
        self.assertEqual(set(schema["$defs"]["entity"]["properties"]["asset_id"]["enum"]), set(PRESENTATION_ASSETS))
        for asset in PRESENTATION_ASSETS.values():
            self.assertTrue((ROOT / "web" / asset.lstrip("/")).is_file())
        for invalid in ("https://example.invalid/a.png", "../private.png", {"src": "x"}):
            self.package["entities"][0]["asset_id"] = invalid
            with self.assertRaises(PackageError):
                validate_package(self.package)

    def test_invalid_unicode_does_not_reach_the_http_renderer(self):
        self.package["title"] = "bad\ud800"
        with self.assertRaises(PackageError):
            validate_package(self.package)

    def test_unknown_database_schema_fails_closed(self):
        self.store.start(self.package, "schema")
        with closing(sqlite3.connect(self.db)) as connection:
            connection.execute("PRAGMA user_version=99")
        with self.assertRaisesRegex(PackageError, "database version"):
            self.store.list()

    def test_host_routes_without_changing_play_session_or_mode(self):
        host = HSRHost.from_options(ROOT.parent, data_root=self.root / ".local")
        request = {"id": "one", "command": "packet_preview_start", "package": self.package, "operation_id": "start"}
        result = host.handle(request)
        self.assertTrue(result["ok"], result)
        preview_id = result["result"]["public_view"]["preview_id"]
        self.assertIsNone(host.mode)
        self.assertFalse(host.booted)
        fresh = HSRHost.from_options(ROOT.parent, data_root=self.root / ".local")
        read = fresh.handle({"id": "two", "command": "packet_preview_read", "preview_id": preview_id})
        self.assertEqual(read["result"]["public_view"], result["result"]["public_view"])
        self.assertFalse((self.root / ".local/reliquary_runs").exists())

    def test_host_interprets_markdown_without_booting_gameplay(self):
        host = HSRHost.from_options(ROOT.parent, data_root=self.root / ".local")
        path = "hollow star scripts/docs/content-compiler-foundation.md"
        source = SourceCatalog(ROOT.parent).read(path, start_line=1, line_count=25)
        reply = host.handle({"id": "draft", "command": "packet_interpret", "path": path,
                             "start_line": 1, "line_count": 25, "expected_sha256": source["sha256"]})
        self.assertTrue(reply["ok"], reply)
        self.assertEqual(reply["result"]["source_verification"], "verified")
        self.assertIn("review_flags", reply["result"])
        self.assertFalse(host.booted)

    def test_host_returns_content_error_and_hosted_relay_blocks_authoring(self):
        host = HSRHost.from_options(ROOT.parent, data_root=self.root / ".local")
        reply = host.handle({"id": "one", "command": "packet_validate", "package": {}})
        self.assertFalse(reply["ok"])
        self.assertEqual(reply["error"]["code"], "CONTENT_INVALID")
        policy = HostedControls(self.root / ".local/hosted_controls.json")
        for command in CONTENT_COMMANDS:
            accepted, code, _ = policy.authorize("gpt", {"command": command})
            self.assertFalse(accepted)
            self.assertEqual(code, "HOSTED_COMMAND_FORBIDDEN")


if __name__ == "__main__":
    unittest.main()
