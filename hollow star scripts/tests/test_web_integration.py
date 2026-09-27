"""Web/CLI/MCP contract checks use isolated saves, never the user's runs."""
import json
import os
import subprocess
import sys
import tempfile
import threading
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import hsr_mcp_server as mcp
import hollowstar_web_server as web
from hollowstar.host import HSRHost
from hollowstar.web_transport import WebHost


def test_browser_cli_mcp_share_one_host():
    with tempfile.TemporaryDirectory(prefix="hsr-web-test-") as temp:
        root = Path(temp)
        host = HSRHost.from_options(data_root=root / ".local")
        with patch.object(web, "_host", host):
            with web.ThreadingHTTPServer(("127.0.0.1", 0), web.Handler) as server:
                thread = threading.Thread(target=server.serve_forever)
                thread.start()
                try:
                    url = f"http://127.0.0.1:{server.server_port}"
                    client = WebHost(url)
                    def call(command, **fields):
                        result = client.handle({"id": "reused-client-id", "command": command, **fields})
                        assert result["ok"], result
                        return result["result"]
                    call("boot", mode="DESIGN")
                    call("create_run", run_id="web-isolated", seed="web-test",
                         party=["divine:Doran"], opposition=["Townsperson"])
                    assert "web-isolated" in call("list_runs")["runs"]
                    call("design_start", run_id="web-isolated")
                    before = call("readout", run_id="web-isolated", public_only=True)["readout"]
                    assert before["public_view"]["schema"] == "hollow-star-public-view-1"
                    assert before["public_view"]["party"][0]["equipment"][0]["display_name"]
                    with urlopen(url + "/api/ui") as response:
                        manifest = json.load(response)
                    assert manifest["schema"] == "hsr-ui-manifest-1" and "equipment" in manifest["screens"]
                    with urlopen(url + "/api/health") as response:
                        assert json.load(response)["ok"]
                    with urlopen(url + "/api/readout?run_id=web-isolated") as response:
                        public = json.load(response)["result"]["readout"]["public_view"]
                    assert public["party"] == before["public_view"]["party"]
                    assert "visible_state" not in json.dumps(public)
                    try:
                        urlopen(url + "/api/readout")
                        raise AssertionError("missing run id accepted")
                    except HTTPError as exc:
                        assert exc.code == 400
                    presentation_assets = ("ui-components.js", "ui-components.css", "ui-polish.js", "character-creation.css", "visual-character-creation.css", "assets/longsword.png", "assets/chain-shirt.png", "assets/townsperson.png", "assets/unidentified-rune.png", *(f"assets/sprites/characters/{race}-{variant}.png" for race in ("human", "elf", "half-elf", "orc", "goblin") for variant in ("female", "male")))
                    for asset in presentation_assets:
                        with urlopen(url + "/web/" + asset) as response:
                            assert response.status == 200 and response.read()
                    for asset in presentation_assets:
                        with urlopen(url + "/" + asset) as response:
                            assert response.status == 200 and response.read()
                    for asset in ("app.js", "hsr-client.js", "styles.css", "character-creation.css", "visual-character-creation.css", "ui-components.js", "ui-components.css"):
                        with urlopen(url + "/" + asset) as response:
                            assert response.status == 200 and response.read()
                    # Exercise the actual compact browser wire envelope too.
                    wire = {"id": "browser", "command": "readout", "run_id": "web-isolated", "public_only": True}
                    with urlopen(Request(url + "/api/host", data=json.dumps(wire).encode(),
                                         headers={"Content-Type": "application/json"}), timeout=10) as response:
                        capsule = json.load(response)
                    assert {k: capsule["view"][k] for k in ("run_id", "room", "party", "available_actions")} == {k: before["public_view"][k] for k in ("run_id", "room", "party", "available_actions")}
                    assert "receipt" in capsule and "visible_state" not in json.dumps(capsule)
                    with patch.dict(os.environ, {"HSR_WEB_URL": url}):
                        bridge = mcp.Bridge()
                        assert isinstance(bridge._host, WebHost)
                        turn = bridge.call("design_turn", {"run_id": "web-isolated",
                            "intent": "party status", "action": {"type": "query", "data": "party_status"},
                            "public_only": True})
                        assert turn["ok"], turn
                        assert turn["view"]["run_id"] == "web-isolated"
                    cli = subprocess.run([sys.executable, str(web.ROOT / "hollowstar_host.py"),
                        "readout", "--web-url", url, "--run-id", "web-isolated", "--public-only"],
                        capture_output=True, text=True, timeout=15)
                    assert cli.returncode == 0, cli.stderr + cli.stdout
                    assert json.loads(cli.stdout)["result"]["readout"]["public_view"]["party"] == turn["view"]["party"]
                    with urlopen(url) as response:
                        page = response.read()
                        assert b"<title>HSR Interface" in page
                    assert b'<main id="app" class="app-shell"' in page
                    with urlopen(url + "/app.js") as response:
                        live_app = response.read()
                    assert b"illustrated-scene" in live_app
                    assert b"from './paperdoll.js" in live_app
                    # The paper doll (layers, poses, champion art) lives in one module.
                    with urlopen(url + "/paperdoll.js") as response:
                        doll = response.read()
                    assert b"scene-character" in doll
                    assert b"SPRITE_LAYER_CATALOG" in doll
                    assert b"data-sprite-layers" in doll
                    assert b"data-sprite-pose" in doll
                    assert b"paperdoll-character" in doll
                    assert b"visualExpression" in doll
                    assert b"expression-${model.expression}" in doll
                    assert b"data-character-identity" in doll
                    for layer in (b"arm:front", b"hand:front", b"brows", b"mouth", b"shoulders"):
                        assert layer in doll
                    # Combat beats are played by the director from public receipts.
                    assert b"from './combat-director.js" in live_app
                    assert b"combatDirector.ingest(previousView, state.view" in live_app
                    with urlopen(url + "/combat-director.js") as response:
                        director = response.read()
                    assert b"export function beatFromReceipt" in director
                    assert b"recent_receipts" in director
                    # Champion pose art must be served, or the doll silently falls back.
                    for pose in ("guard", "overhead-strike", "sweep", "rest", "low-ready"):
                        with urlopen(f"{url}/assets/sprites/characters/doran/doran-{pose}.png") as response:
                            assert response.status == 200
                    assert b"atmosphere" in live_app
                    for path in ("/host_config.json", "/.local/hosted_controls.json", "/../readme.md"):
                        try:
                            urlopen(url + path)
                            raise AssertionError("private path exposed")
                        except HTTPError as exc:
                            assert exc.code == 404
                    try:
                        urlopen(Request(url + "/api/host", data=json.dumps(wire).encode(), headers={
                            "Content-Type": "application/json", "Origin": "https://unrelated.example"}))
                        raise AssertionError("foreign origin accepted")
                    except HTTPError as exc:
                        assert exc.code == 403
                finally:
                    server.shutdown()
                    thread.join(timeout=5)



def test_creation_client_contract_hides_lead_identity_and_exposes_accessible_controls():
    app = (Path(__file__).resolve().parents[1] / "web" / "app.js").read_text(encoding="utf-8")
    assert "Lead identity" not in app
    assert "['female', 'male', 'other']" in app and 'data-choice="gender:' in app
    assert "randomize-build" in app and "surprise-step" in app and "allocate_creation_seed" in app
    # Town-only controls are withheld once the run leaves Floor One, not sent and refused.
    assert "function floorOneWorld" in app and "floorOneWorld() ? `${button(scene.travel?.active" in app
    assert "function attackSpent" in app
    assert "aria-current=\"${index === current ? 'step' : 'false'}\"" in app
    assert "Show deterministic creation receipt" in app
    assert "hsr-console" in app


def test_public_launch_roles_are_mode_scoped_in_the_browser():
    app = (Path(__file__).resolve().parents[1] / "web" / "app.js").read_text(encoding="utf-8")
    styles = (Path(__file__).resolve().parents[1] / "web" / "styles.css").read_text(encoding="utf-8")
    assert "Story Mode can begin with Doran or Wren" in app
    assert "Choose a Champion or create an adventurer for the Reliquary’s authored story.'" in app
    assert "Simulation Mode accepts custom profiles and certified Champions" in app
    assert "const forge = state.pendingMode === 'FORGE';" in app
    assert "if (mode !== 'SANDBOX') throw Error('Custom characters are available only in Simulation Mode.');" not in app
    assert "scenario: scenarioFor(mode)" in app
    assert "statistics-save:" in app
    assert "calc(100dvh * 2)" in styles and "calc(100vw / 2)" in styles
    assert ".mode-menu-card:has(.run-list) .run-list" in styles
    assert app.count('return `<div class="mode-menu">') >= 6
    assert 'class="menu-viewport" data-menu-viewport' in app
    assert ".menu-viewport{min-width:0;min-height:0;height:100%;overflow-y:auto" in styles
    assert "body:has(.menu-viewport) #app.app-shell>.menu-viewport{min-height:0;max-height:100%}" in styles
    assert "body{padding-bottom:0}" in styles
    assert "options-section" in app and "<summary>" in app
    assert ".menu-viewport::-webkit-scrollbar{display:none;width:0;height:0}" in styles
    stage = (Path(__file__).resolve().parents[1] / "web" / "stage.css").read_text(encoding="utf-8")
    assert "transform:translate(-50%,-50%) scale(var(--stage-scale))" in stage
    assert "position:static;left:auto;top:auto;width:auto" in stage
    assert "DEFAULT_CHAMPIONS" not in app


def test_browser_entry_module_parses_before_the_interface_is_served():
    """Keep a misplaced UI callback from turning startup into a blank recovery screen."""
    app = Path(__file__).resolve().parents[1] / "web" / "app.js"
    parsed = subprocess.run(
        ["node", "--input-type=module", "--check"], input=app.read_text(encoding="utf-8"),
        capture_output=True, text=True, encoding="utf-8", timeout=15,
    )
    assert parsed.returncode == 0, parsed.stderr


def test_title_connection_readout_updates_without_gameplay_workspace_status():
    app = (Path(__file__).resolve().parents[1] / "web" / "app.js").read_text(encoding="utf-8")
    styles = (Path(__file__).resolve().parents[1] / "web" / "styles.css").read_text(encoding="utf-8")
    ui = (Path(__file__).resolve().parents[1] / "web" / "ui-components.css").read_text(encoding="utf-8")
    index = (Path(__file__).resolve().parents[1] / "web" / "index.html").read_text(encoding="utf-8")
    refresh = app.split("function refreshLinkReadout() {", 1)[1].split("let heartbeatInFlight", 1)[0]
    assert "const boxes = document.querySelectorAll('[data-workspace-status]');" in refresh
    assert "if (!boxes.length) return;" not in refresh
    assert ".intro-connection [data-link]" in refresh
    assert "state.link.status = beat.ok ? 'online' : 'offline';" in app
    assert "A text-driven roleplaying adventure" not in app
    assert "From the Divine Mythos comes Ember and Sera's greatest plaything..." not in app
    assert 'class="intro-title-the">The</span>' in app
    assert 'class="intro-title-main">Hollow<br>Star</span>' in app
    assert 'class="intro-title-sub">Reliquary</span>' in app
    assert ">Local</span></button>" in app
    assert "connection-status" not in app
    assert "min-width: 78px" in styles  # gameplay/workspace connection layout remains unchanged
    assert ".intro-card > .intro-connection" in ui
    assert 'font-family: var(--font-display)' in ui
    assert "Cormorant+Garamond" not in index
    assert "margin: 46px 0 22px" in ui


def test_encounter_screen_tracks_host_combat_lifecycle_and_valid_targets():
    app = (Path(__file__).resolve().parents[1] / "web" / "app.js").read_text(encoding="utf-8")
    target_block = app.split("function actionTargets(action) {", 1)[1].split("function targetPicker() {", 1)[0]
    assert "function encounterActive(" in app
    assert "syncEncounterScreen(previousView, state.view)" in app
    # Arcade and turn-based fights both live in Encounters (the expedition hub).
    assert "if (arcadeActive(nextView) && !arcadeActive(previousView)) selectGameplayScreen('battle')" in app
    assert "else if (tacticalActive(nextView) && !tacticalActive(previousView)) selectGameplayScreen('battle')" in app
    assert "selectGameplayScreen(nextView?.expedition?.active ? 'battle' : 'room')" in app
    journey = app.split("function journey() {", 1)[1].split("function autoToggle() {", 1)[0]
    arcade = app.split("function arcadeEncounter() {", 1)[1].split("const XP_MODES", 1)[0]
    battle = app.split("function battle() {", 1)[1].split("// Hosts send statuses as a list", 1)[0]
    assert "${arcadeStage()}" not in journey and "${arcadeControls()}" not in journey
    assert "${arcadeStage()}" in arcade and "${arcadeControls()}" in arcade
    assert "if (arcadeActive(v)) return arcadeEncounter();" in battle
    assert "tacticalActive(v)" in battle and "return ffBattle();" in battle
    assert "return expeditionHub();" in battle
    assert "state.view?.opposition" in target_block
    assert "room.npcs" in target_block
    assert "action === 'move' || ['move_room', 'enter'].includes(action)" in target_block
    assert "rawValue.includes(',') ? rawValue.split(',').map(Number) : rawValue" in app
    assert "stepActor.startsWith('p')" in app
    assert "Advance NPC turn" in app


def test_life_world_action_bar_preserves_host_type_affordances():
    app = (Path(__file__).resolve().parents[1] / "web" / "app.js").read_text(encoding="utf-8")
    block = app.split("function actionBar() {", 1)[1].split("const FOCUS_ATTRS", 1)[0]
    assert "if (state.phase !== 'ready') return '';" in block
    assert "row.id || row.action || row.type" in block
    assert "life action never degrades into an empty" in app


def test_transport_refuses_nonlocal_url():
    for url in ("https://127.0.0.1", "http://example.com", "http://user@localhost", "http://localhost/private"):
        try:
            WebHost(url)
            raise AssertionError("nonlocal or ambiguous URL accepted")
        except ValueError:
            pass


def test_menu_focus_and_secondary_interactions_are_client_only():
    root = Path(__file__).resolve().parents[1]
    app = (root / "web" / "app.js").read_text(encoding="utf-8")
    page = (root / "web" / "index.html").read_text(encoding="utf-8")
    # These three used to be stubbed to return '' outright (a former
    # consolidation attempt that was never finished, leaving the Options
    # screen's Connections/Information/Clock toggles silently inert). They
    # now render real panels gated by their own show* preference instead.
    assert "local-activity" in app
    assert "secondaryInteractions" in app and "context-primary" in app
    assert "Choose a Champion or create an adventurer for the Reliquary’s authored story." in app
    assert "The authored First Threshold." not in app
    assert "A private sandbox for rehearsal." in app


def test_screen_refresh_and_overlay_stack_keep_navigation_immediate_and_clean():
    root = Path(__file__).resolve().parents[1]
    app = (root / "web" / "app.js").read_text(encoding="utf-8")
    styles = (root / "web" / "styles.css").read_text(encoding="utf-8")
    assert "function refreshScreen(screen = state.selected)" in app
    assert "document.querySelectorAll('#app .combat-float, #app .hsr-context-menu')" in app
    assert "navigate: screen => state.phase === 'ready' ? refreshScreen(screen) : false" in app
    assert "setTimeout(() => node.click()" not in app
    assert "if (app && !app.dataset.contextDismiss)" in app
    assert ".hsr-context-menu{z-index:var(--z-context);pointer-events:auto}" in styles
    assert ".breadcrumb-link" in styles
    assert "function resetRunStateForLoad()" in app
    assert "state.receipt = null" in app and "state.messageHistory = []" in app
    assert "const mode = String(inspected.result?.run?.context?.host_mode" in app
    assert "result(await state.client.loadRun(id)); await loadReadout(id);" in app


def test_dynamic_panels_render_imprints_objects_and_signatures():
    root = Path(__file__).resolve().parents[1]
    app = (root / "web" / "app.js").read_text(encoding="utf-8")
    styles = (root / "web" / "styles.css").read_text(encoding="utf-8")

    # 1. Reliquary Imprints Panel Contract
    assert "function imprintPanel()" in app
    assert "state.view?.imprints" in app
    assert 'class="imprint-grid"' in app
    assert 'class="imprint-slot"' in app
    assert ".imprint-grid" in styles
    assert ".imprint-slot" in styles

    # 2. Room Objects Panel Contract
    assert "function roomObjects()" in app
    assert "state.view?.room?.objects" in app
    assert 'class="room-objects"' in app
    assert 'class="object-row"' in app
    assert "objectActions(obj)" in app

    # 3. Signature Actions for Champions Contract
    assert "function signatureActions()" in app
    assert "identity === 'wren'" in app and "Wren's domain" in app
    assert "data-domain-feature=" in app
    assert "identity === 'doran'" in app and "Doran's maneuvers" in app
    assert "data-maneuver=" in app


def test_starting_entry_flow_and_auto_connect_contract():
    root = Path(__file__).resolve().parents[1]
    app = (root / "web" / "app.js").read_text(encoding="utf-8")
    styles = (root / "web" / "styles.css").read_text(encoding="utf-8")

    assert "function entrySelect()" in app
    assert "start-story:well" in app and "start-story:market" in app
    assert "back-to-lead" in app
    assert ".entry-select-hero" in styles
    assert ".entry-path-grid" in styles
    assert "beginCustomRun(profileId" in app
    assert "state.pendingLead = {kind: 'champion', name: champ}" in app
