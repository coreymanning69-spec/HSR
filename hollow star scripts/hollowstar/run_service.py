"""One authoritative Run service over Actor/Encounter/RunRNG/save-resume.

This is the single boundary a host process uses to create, list, inspect,
persist, and resume a Run. Nothing outside this module should construct an
Encounter and hand-save it: that forks a second, invisible Run lifecycle the
host can no longer account for. Any future adapter -- the stdio host today,
the terminal screen -- must read and write Run state through here so the
two can never disagree about what a run_id currently holds.

The service owns the shared Run schema for DESIGN, REVIEW, SANDBOX, and FORGE.
Mode policy is enforced at host boot; SANDBOX and FORGE remain isolated from
canon even though they use the same persistence and transition boundary.
"""

from __future__ import annotations

import copy
import base64
import hashlib
import json
import re
from dataclasses import dataclass, field
from pathlib import Path

from hollowstar.actors import Actor
from hollowstar.combat import Encounter
from hollowstar.loader import load_roster
from hollowstar.profiles import ProfileError, ProfileService, actor_sheet
from hollowstar.rng import RunRNG
from hollowstar.run_state import RunStateError, resume_run, save_run as _save_run
from hollowstar.snapshot import import_party, load_snapshot
from hollowstar.modules import ModuleError, load_module, load_module_content, module_roster
from hollowstar.storage import atomic_json

_RUN_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]+$")


#: Forge is the authored Story runtime. Doran and Wren remain the certified
#: Champion launch pair; custom profiles are admitted only to the authored
#: city opening and never receive Champion identity rules.
FORGE_PARTY = frozenset({"Doran", "Wren"})
LAUNCH_ROLES = frozenset({"CHAMPION", "CUSTOM", "SUPPORTED"})

#: Threshold verbs that stay Forge-owned even once its world is running, so a
#: canon-candidate receipt can still be cut mid-run.
FORGE_RECEIPT_ACTIONS = frozenset({"complete", "promote_candidate", "resolve", "threshold"})


def selector_name(selector: str) -> str:
    """The actor name a party selector resolves to, without loading it."""
    if selector.startswith("custom:"):
        return ""
    if selector.startswith(("divine:", "hsr:")):
        return selector.split(":", 1)[1]
    return selector


def runtime_for(party: list[str]) -> str:
    """The runtime a party belongs in: Forge for Stewards, Sandbox otherwise."""
    names = {selector_name(s) for s in party}
    return "FORGE" if names and names <= set(FORGE_PARTY) else "SANDBOX"


def launch_role_for(party: list[str]) -> str:
    """Classify a party for launch routing, independently of gameplay roles."""
    if not isinstance(party, list) or not party or not all(isinstance(row, str) for row in party):
        raise RunServiceError("party must be a non-empty list of selectors")
    if any(row.startswith("custom:") for row in party):
        return "CUSTOM"
    names = {selector_name(row) for row in party}
    if names and names <= set(FORGE_PARTY):
        return "CHAMPION"
    return "SUPPORTED"


def validate_launch(*, mode: str, party: list[str], scenario: str,
                    module_id: str | None = None,
                    require_authored_module: bool = False) -> dict:
    """Validate the public launch contract before any run state is created."""
    normalized_mode = str(mode).upper() if isinstance(mode, str) else ""
    if normalized_mode not in {"DESIGN", "REVIEW", "SANDBOX", "FORGE"}:
        raise RunServiceError("run_mode must be DESIGN, REVIEW, SANDBOX, or FORGE")
    role = launch_role_for(party)
    scenario_row = next((row for row in RunService.SCENARIO_CATALOG
                         if row["scenario"] == scenario), None)
    if scenario_row is None:
        raise RunServiceError(
            f"unknown scenario {scenario!r}; expected one of {sorted(RunService.SCENARIOS)}"
        )
    if normalized_mode == "FORGE" and role == "CUSTOM" and scenario != "reliquary_city":
        raise RunServiceError(
            "Story custom characters must enter through the authored reliquary_city route"
        )
    if normalized_mode == "FORGE" and role == "SUPPORTED":
        outsiders = sorted({selector_name(row) for row in party if selector_name(row) not in FORGE_PARTY and selector_name(row)})
        raise RunServiceError(
            "Story Mode requires a Doran or Wren Champion; use Simulation Mode (SANDBOX) for "
            + ", ".join(outsiders or ["unsupported party members"])
        )
    if normalized_mode == "FORGE" and require_authored_module and module_id != "reliquary-template":
        raise RunServiceError("Story Mode requires the authored reliquary-template module")
    return {"mode": normalized_mode, "launch_role": role, "scenario": scenario}


class RunServiceError(RunStateError):
    """Raised for a Run-service-level request that cannot be satisfied."""


def _validate_run_id(run_id: str) -> str:
    if not isinstance(run_id, str) or not _RUN_ID_PATTERN.fullmatch(run_id):
        raise RunServiceError(
            f"run_id must be non-empty and match {_RUN_ID_PATTERN.pattern}: {run_id!r}"
        )
    return run_id


def _pick(roster: dict[str, Actor], name: str, label: str) -> Actor:
    if name not in roster:
        raise RunServiceError(
            f"unknown {label} actor {name!r}; available: {sorted(roster)}"
        )
    return copy.deepcopy(roster[name])


def _actor_summary(actor: Actor) -> dict:
    return {
        "name": actor.name,
        "sprite_id": actor.sprite_id,
        "hp": actor.hp,
        "max_hp": actor.max_hp,
        "alive": actor.alive,
        "armor_class": actor.armor_class,
    }


@dataclass
class RunSummary:
    """A read-only, JSON-safe view of a Run. Never the Encounter itself."""

    run_id: str
    mode: str
    seed: object
    round_number: int
    finished: bool
    winner: str | None
    party: list[dict] = field(default_factory=list)
    opposition: list[dict] = field(default_factory=list)
    context: dict = field(default_factory=dict)

    def as_dict(self) -> dict:
        return {
            "run_id": self.run_id,
            "mode": self.mode,
            "seed": self.seed,
            "round_number": self.round_number,
            "finished": self.finished,
            "winner": self.winner,
            "party": self.party,
            "opposition": self.opposition,
            "context": copy.deepcopy(self.context),
        }


def summarize(run_id: str, encounter: Encounter) -> RunSummary:
    sandbox_state = encounter.context.get("sandbox")
    finished = (sandbox_state.get("status") != "active"
                if isinstance(sandbox_state, dict) else encounter.finished())
    winner = None
    if finished:
        if isinstance(sandbox_state, dict):
            winner = "party" if sandbox_state.get("status") in {"cleared", "escaped"} else "sandbox"
        else:
            winner = "party" if any(a.alive for a in encounter.party) else "opposition"
    context = {k:v for k,v in encounter.context.items()
               if k in {"world","party_selectors","party_identity","launch_track","run_launch","module","scenario","host_mode"}}
    if isinstance(sandbox_state, dict):
        context["sandbox"] = {
            "schema": sandbox_state.get("schema"), "status": sandbox_state.get("status"),
            "rules_version": sandbox_state.get("rules_version"),
            "current_room": sandbox_state.get("current_room"), "prestige": copy.deepcopy(sandbox_state.get("prestige")),
            "finished_record": sandbox_state.get("finished_record"),
        }
    if "module" in context and "module_content" in encounter.context:
        content = encounter.context["module_content"]
        context["module"] = copy.deepcopy(context["module"])
        context["module"]["content_counts"] = {
            key: sum(len(value) for value in payload.values() if isinstance(value, list))
            for key, payload in content.items() if isinstance(payload, dict)
        }
    return RunSummary(
        run_id=run_id,
        mode=encounter.mode,
        seed=encounter.rng.seed,
        round_number=encounter.round_number,
        finished=finished,
        winner=winner,
        party=[_actor_summary(a) for a in encounter.party],
        opposition=[_actor_summary(a) for a in encounter.opposition],
        context=copy.deepcopy(context),
    )


class RunService:
    """Owns every Run a booted host process currently has open.

    Party selectors resolve locked Divine Mythos imports or local custom profiles.
    Each run freezes its selected baselines; subsequent profile edits affect only
    newly created runs. Both the terminal and JSON host use this boundary.
    """

    # One catalog drives validation, the host's scenario_catalog command, and the
    # client's Edit Scenario screen, so a scenario can never be offered here and
    # rejected by create(), or accepted by create() and invisible to a player.
    SCENARIO_CATALOG = (
        {"scenario": "champion_rehearsal", "title": "Champion Rehearsal",
         "blurb": "Custom equipment-driven encounter fixtures; not balance-certified.",
         "modes": ("SANDBOX", "DESIGN")},
        {"scenario": "floor_one_life", "title": "Floor One Life",
         "blurb": "The default Simulation loop: one floor, a living account, and "
                  "banked progression between rehearsal runs.",
         "modes": ("SANDBOX", "DESIGN")},
        {"scenario": "reliquary_city", "title": "Reliquary City",
         "blurb": "The city gauntlet above the Reliquary. Same life account as Floor "
                  "One Life, with the city's travel, vendors, and street encounters.",
         "modes": ("SANDBOX", "DESIGN", "FORGE")},
        {"scenario": "dd_sandbox", "title": "Dungeon Delve Sandbox",
         "blurb": "A bare rehearsal encounter with no life account attached — the "
                  "quickest surface for testing a build, an item, or a maneuver.",
         "modes": ("SANDBOX", "DESIGN")},
        {"scenario": "reliquary", "title": "Reliquary Descent",
         "blurb": "The authored five-floor module. Story Mode runs it against the "
                  "reliquary-template manifest; it is not a Simulation surface.",
         "modes": ("FORGE",)},
    )
    SCENARIOS = {row["scenario"] for row in SCENARIO_CATALOG}

    @classmethod
    def scenario_catalog(cls, mode: str | None = None) -> list[dict]:
        """Public scenario rows, optionally narrowed to one run mode."""
        wanted = mode.upper() if isinstance(mode, str) and mode else None
        return [
            {"scenario": row["scenario"], "title": row["title"],
             "blurb": row["blurb"], "modes": list(row["modes"])}
            for row in cls.SCENARIO_CATALOG
            if wanted is None or wanted in row["modes"]
        ]

    def __init__(self, run_root: Path | str, snapshot_path: Path | str | None = None,
                 profile_root: Path | str | None = None, module_root: Path | str | None = None,
                 finished_root: Path | str | None = None, *, durable_saves: bool = True):
        self.run_root = Path(run_root)
        self.snapshot_path = Path(snapshot_path) if snapshot_path else None
        self.profile_root = Path(profile_root) if profile_root else self.run_root.parent / "reliquary_profiles"
        self.module_root = Path(module_root) if module_root else self.run_root.parent / "content" / "modules"
        self.finished_root = Path(finished_root) if finished_root else self.run_root.parent / "reliquary_finished_runs"
        self.durable_saves = durable_saves
        self._active: dict[str, Encounter] = {}
        self._active_sandbox_run_id: str | None = None

    def content_previews(self):
        """Authoring sessions live outside playable saves and account retention.

        The same service owns persistence, but these records are not Encounters:
        inspecting a compiler packet never grants items, runs dice, or settles XP.
        """
        from hollowstar.content_preview import PreviewStore
        return PreviewStore(self.run_root.parent / "content_workbench" / "previews.sqlite3")

    def _path_for(self, run_id: str) -> Path:
        _validate_run_id(run_id)
        return self.run_root / f"{run_id}.json"

    def create(self, run_id: str, party: list[str], opposition: list[str], seed: str | int,
               *, module_id: str | None = None, scenario: str = "reliquary",
               run_mode: str = "DESIGN", lead_selector: str | None = None,
               starting_location: str | None = None) -> RunSummary:
        path = self._path_for(run_id)
        if path.exists():
            raise RunServiceError(f"run already exists: {run_id}")
        if not isinstance(party, list) or not all(isinstance(x, str) for x in party):
            raise RunServiceError("party must be a list of selectors")
        if not isinstance(opposition, list) or not all(isinstance(x, str) for x in opposition):
            raise RunServiceError("opposition must be a list of names")
        if isinstance(seed, int) and not isinstance(seed, bool):
            seed = str(seed)
        if not isinstance(seed, str) or not seed:
            raise RunServiceError("seed must be a non-empty string or integer")
        if not party:
            raise RunServiceError("a run requires at least one party member")
        if len(set(party)) != len(party):
            raise RunServiceError("party selectors must be unique")
        if lead_selector is None:
            lead_selector = party[0]
        if not isinstance(lead_selector, str) or lead_selector not in party:
            raise RunServiceError("lead_selector must name one selected party member")
        if not opposition:
            raise RunServiceError("a run requires at least one opposition member")
        if not isinstance(run_mode, str) or run_mode.upper() not in {"DESIGN", "REVIEW", "SANDBOX", "FORGE"}:
            raise RunServiceError("run_mode must be DESIGN, REVIEW, SANDBOX, or FORGE")
        run_mode = run_mode.upper()
        if scenario == "champion_rehearsal" and module_id is None:
            module_id = "wren-boss-rehearsal"
        validate_launch(mode=run_mode, party=party, scenario=scenario, module_id=module_id)
        certified, _ = import_party(self.snapshot_path)
        profiles = ProfileService(self.profile_root, self.snapshot_path)
        stock = load_roster()
        selected = []
        for selector in party:
            try:
                if selector.startswith("custom:"):
                    selected.append(profiles.actor(selector.split(":", 1)[1]))
                elif selector.startswith("hsr:"):
                    name = selector.split(":", 1)[1]
                    selected.append(_pick(stock, name, "party"))
                else:
                    name = selector.split(":", 1)[1] if selector.startswith("divine:") else selector
                    selected.append(_pick(certified, name, "party"))
            except ProfileError as exc:
                raise RunServiceError(str(exc)) from exc
        module = None
        if module_id is not None:
            if not isinstance(module_id, str) or not module_id:
                raise RunServiceError("module_id must be a non-empty string")
            try:
                module_path = self.module_root / module_id / "manifest.json"
                module = load_module(module_path)
                module_content = load_module_content(module_path, module)
            except ModuleError as exc:
                raise RunServiceError(str(exc)) from exc
            if module["module_id"] != module_id:
                raise RunServiceError("module manifest identity does not match module_id")
            # Authored module actors join the selectable roster for this run
            # only. Stock names win a collision so a module can never shadow a
            # certified actor; the module keeps its actor_id as the safe handle.
            for key, actor in module_roster(module_content).items():
                if key not in stock:
                    stock[key] = actor
        encounter = Encounter(
            party=selected,
            opposition=[_pick(stock, name, "opposition") for name in opposition],
            rng=RunRNG(seed),
        )
        custom_profiles = {s: profiles._load(s.split(":", 1)[1]) for s in party if s.startswith("custom:")}
        identities = [profiles.inspect(s.split(":", 1)[1]).get("identity", {})
                      if s.startswith("custom:") else {} for s in party]
        if lead_selector.startswith("custom:"):
            lead_profile = custom_profiles[lead_selector]
            starting_gold = int(lead_profile["build_rules"].get("starting_gold", 10))
            launch_source = str(lead_profile["build_rules"].get("starting_gold_source", "legacy_default"))
        else:
            starting_gold = 10
            launch_source = "premade_default"
        encounter.context.update({"party_selectors": list(party), "party_identity": identities,
                                  "run_launch": {"schema": "hollow-star-run-launch-1", "lead_selector": lead_selector,
                                                 "starting_gold": starting_gold, "source": launch_source},
                                  "launch_track": "custom" if all(s.startswith("custom:") for s in party)
                                  else "mixed" if any(s.startswith("custom:") for s in party) else "stewards"})
        encounter.context["scenario"] = scenario
        if starting_location:
            encounter.context["starting_location"] = str(starting_location)
        if scenario in {"floor_one_life", "reliquary_city"}:
            # Floor One is a run mode, not a second persistence authority.
            encounter.context["progression_root"] = str(self.run_root.parent / "reliquary_progress")
        encounter.context["host_mode"] = run_mode
        if module is not None:
            # Preserve the validated contract, not a live path, so the run is
            # replayable and cannot silently change when content is edited.
            encounter.context["module"] = copy.deepcopy(module)
            encounter.context["module_content"] = module_content
        snapshot = load_snapshot(self.snapshot_path)
        party_rules = {}
        for index, selector in enumerate(party):
            if selector.startswith("custom:"):
                data = custom_profiles[selector]
                party_rules[f"p{index}"] = copy.deepcopy(data.get("build_rules", {}))
            elif selector.startswith("hsr:"):
                party_rules[f"p{index}"] = {
                    "identity": selected[index].name.lower(),
                    "level": selected[index].provenance.snapshot_version,
                    "baseline_resources": dict(selected[index].resources),
                    "base_ac": selected[index].armor_class,
                    "deferred": list(selected[index].provenance.deferred),
                }
            else:
                name = selected[index].name.lower()
                source = snapshot["characters"][name]["certified"]
                party_rules[f"p{index}"] = {"identity": name, "level": 20,
                    "saves": {k.upper(): v for k,v in source["stats"].get("saves", {}).items()},
                    "baseline_resources": dict(selected[index].resources),
                    "base_ac": selected[index].armor_class}
        encounter.context["party_rules"] = party_rules
        from hollowstar.progression import Progression
        progress=Progression(self.run_root.parent / "reliquary_progress")
        encounter.context["earned_progress"]={selector:progress.load(selector if ":" in selector else "divine:"+selector) for selector in party}
        lead_identity = lead_selector if ":" in lead_selector else "divine:" + lead_selector
        account = progress.migrate_life_account(lead_identity) if scenario in {"floor_one_life", "reliquary_city"} else progress.load(lead_identity)
        encounter.context["account_identity"] = lead_identity
        # Immutable launch snapshot: replay identity cannot drift with later
        # purchases, settlements, or loop-tier changes.
        meta = {"account_id": account["account_id"], "rank": account["rank"],
                "rank_xp": account["rank_xp"], "platinum": account["platinum"],
                "upgrades": copy.deepcopy(account["upgrades"]), "loop_tier": account["loop_tier"]}
        encounter.context["account_meta"] = meta
        encounter.context["account_meta_hash"] = hashlib.sha256(json.dumps(meta, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        # Loop tier is frozen at launch from the lead's account progress, not
        # re-read later: a run in progress must keep playing at the tier it
        # started, even if a different run for the same identity settles and
        # advances the account's tier while this one is still open.
        encounter.context["loop_tier"] = encounter.context["earned_progress"][lead_selector].get("loop_tier", 1)
        if self.durable_saves:
            _save_run(encounter, run_id, path, snapshot_version="hsr-selectable-party-1")
        self._active[run_id] = encounter
        return summarize(run_id, encounter)

    def load(self, run_id: str) -> RunSummary:
        path = self._path_for(run_id)
        if not path.exists():
            raise RunServiceError(f"no such run: {run_id}")
        try:
            encounter = resume_run(path, expected_run_id=run_id)
        except RunStateError as exc:
            raise RunServiceError(str(exc)) from exc
        self._active[run_id] = encounter
        if isinstance(encounter.context.get("sandbox"), dict):
            self._active_sandbox_run_id = run_id
        return summarize(run_id, encounter)

    def inspect(self, run_id: str) -> RunSummary:
        if run_id in self._active:
            return summarize(run_id, self._active[run_id])
        path = self._path_for(run_id)
        if not path.exists():
            raise RunServiceError(f"no such run: {run_id}")
        try:
            return summarize(run_id, resume_run(path, expected_run_id=run_id))
        except RunStateError as exc:
            raise RunServiceError(str(exc)) from exc

    def save(self, run_id: str) -> RunSummary:
        encounter = self._active.get(run_id)
        if encounter is None:
            raise RunServiceError(f"run is not loaded: {run_id}; load it first")
        _save_run(encounter, run_id, self._path_for(run_id))
        return summarize(run_id, encounter)

    def probe_package_effect(self, run_id, package, effect_id, *, since=0, catalog=None):
        """Read active or saved event-clock counters; never load, save or tick a run."""
        from hollowstar.runtime_hooks import evaluate_effect
        from hollowstar.runtime_contract import compile_package
        from hollowstar.clock import SCHEMA as CLOCK_SCHEMA
        self._path_for(run_id)
        run = self._active.get(run_id)
        if run is None:
            run = resume_run(self._path_for(run_id), expected_run_id=run_id)
        sealed = compile_package(package, catalog)["package"]
        effect = next((row for row in sealed["effects"] if row["id"] == effect_id), None)
        if effect is None:
            raise RunServiceError("unknown effect ID")
        # Prefer the active life-world clock, as observe() does; never create one.
        world = run.context.get("life_world") or run.context.get("dungeon") or {}
        event_clock = world.get("event_clock", {})
        counter = {"turn_end": "turn", "round_start": "round", "world_tick": "seconds"}[effect["tick_phase"]]
        current = event_clock.get(counter)
        if event_clock.get("schema") != CLOCK_SCHEMA or type(current) is not int or current < 0:
            raise RunServiceError("run has no valid event clock for this phase")
        if type(since) is not int or not 0 <= since <= current:
            raise RunServiceError("since must be an integer between zero and the current phase counter")
        result = evaluate_effect(sealed, effect_id, elapsed=current - since, catalog=catalog)
        return {**result, "run_id": run_id, "clock_counter": counter, "clock_value": current,
                "since": since, "state_committed": False}

    def replay_token(self, run_id: str) -> dict:
        encounter = self._active.get(run_id)
        if encounter is None:
            raise RunServiceError("load the run first")
        contract = encounter.context.get('replay_contract')
        if not isinstance(contract, dict):
            raise RunServiceError('replay metadata is unavailable until the dungeon starts')
        payload = {**copy.deepcopy(contract),'schema':'hollow-star-replay-token-1',
                   'run_id':run_id,'seed':encounter.rng.seed}
        encoded = base64.urlsafe_b64encode(json.dumps(payload, sort_keys=True, separators=(',', ':')).encode()).decode().rstrip('=')
        return {'token':encoded,'payload':payload,'read_only':True}

    @staticmethod
    def inspect_replay_token(token: str) -> dict:
        if not isinstance(token, str) or not token:
            raise RunServiceError('replay token must be a non-empty string')
        try:
            padded=token + '=' * (-len(token) % 4)
            payload=json.loads(base64.urlsafe_b64decode(padded.encode()).decode())
        except (ValueError, TypeError, UnicodeError, json.JSONDecodeError) as exc:
            raise RunServiceError('invalid replay token') from exc
        if not isinstance(payload, dict) or payload.get('schema') != 'hollow-star-replay-token-1':
            raise RunServiceError('unsupported replay token schema')
        return {'payload':payload,'read_only':True,'continuation':'disabled until engine and content fingerprints match'}

    def list(self) -> list[str]:
        if not self.run_root.exists():
            return []
        return sorted(p.stem for p in self.run_root.glob("*.json"))

    def sheets(self, run_id: str) -> list[dict]:
        self._path_for(run_id)
        encounter = self._active.get(run_id)
        if encounter is None:
            encounter = resume_run(self._path_for(run_id), expected_run_id=run_id)
        selectors = encounter.context.get("party_selectors", [])
        identities = encounter.context.get("party_identity", [])
        out = []
        for index, actor in enumerate(encounter.party):
            selector = selectors[index] if index < len(selectors) else f"party:{index}"
            sheet = actor_sheet(actor, selector=selector, kind="run")
            sheet["editable"] = False
            sheet["party_index"] = index
            if index < len(identities) and identities[index]:
                sheet["identity"] = copy.deepcopy(identities[index])
            out.append(sheet)
        return copy.deepcopy(out)

    def design_start(self, run_id: str) -> dict:
        encounter = self._active.get(run_id)
        if encounter is None:
            raise RunServiceError("load the run first")
        # Story Mode enters the authored first village before the generic
        # Forge threshold.  The host remains FORGE/champion-only, but this
        # scenario is an actual social world with public residents, state,
        # and a later descent into the ordinary dungeon engine.
        if encounter.context.get("scenario") in {"floor_one_life", "reliquary_city"}:
            from hollowstar import life_sim
            if isinstance(encounter.context.get("life_world"), dict):
                return {"event": {"type": "life_world_resumed", "evidence": {"state_reused": True}},
                        "state": life_sim.view(encounter)}
            return self._transition(run_id, life_sim.start, action_label="life_world_start")
        if encounter.context.get("host_mode") == "FORGE" or isinstance(encounter.context.get("forge"), dict):
            return self.forge_start(run_id)
        if encounter.context.get("scenario") == "dd_sandbox":
            return self.sandbox_start(run_id)
        from hollowstar import dungeon
        if "dungeon" in encounter.context:
            return {
                "event": {
                    "type": "dungeon_resumed",
                    "room": dungeon.public_room(dungeon.room(encounter)),
                    "evidence": {"already_started": True, "state_reused": True},
                },
                "state": dungeon.view(encounter),
            }
        return self._transition(run_id, dungeon.start, action_label="design_start")

    def design_action(self, run_id: str, action: dict, *, intent: str | None = None,
                      include_state: bool = True) -> dict:
        if not isinstance(action, dict):
            raise RunServiceError("action must be an object")
        if intent is not None and (not isinstance(intent, str) or not intent.strip()):
            raise RunServiceError("intent must be a non-empty string when supplied")
        original = self._active.get(run_id)
        if (original is not None and isinstance(original.context.get("forge"), dict)
                and str(action.get("type", "")).lower() in FORGE_RECEIPT_ACTIONS):
            return self._forge_transition(run_id, action, player_intent=intent)
        if original is not None and isinstance(original.context.get("sandbox"), dict):
            from hollowstar import sandbox
            return self._transition(run_id, lambda run: sandbox.act(run, action),
                                     action_label=action.get("type"),
                                     player_intent=intent.strip() if intent else None,
                                     include_state=include_state)
        if original is not None and isinstance(original.context.get("life_world"), dict):
            from hollowstar import life_sim
            if original.context.get("scenario") == "reliquary_city" and action.get("type") in {
                    "descend", "enter_gauntlet", "enter_reliquary"}:
                from hollowstar import dungeon

                def descend(run):
                    result = life_sim.act(run, action)
                    if result.get("event", {}).get("type") != "descent_started":
                        return result
                    run.context["city_world"] = run.context.pop("life_world")
                    dungeon_result = dungeon.start(run)
                    dungeon_result["descent"] = result["event"]
                    return dungeon_result

                return self._transition(run_id, descend,
                                        action_label=action.get("type"),
                                        player_intent=intent.strip() if intent else None,
                                        include_state=include_state)
            return self._transition(run_id, lambda run: life_sim.act(run, action),
                                     action_label=action.get("type"),
                                     player_intent=intent.strip() if intent else None,
                                     include_state=include_state)
        from hollowstar import dungeon
        return self._transition(run_id, lambda run: dungeon.act_and_advance(run, action),
                                action_label=action.get("type"),
                                player_intent=intent.strip() if intent else None,
                                include_state=include_state)

    def idle_tick(self, run_id: str, *, max_steps: int = 1) -> dict:
        """Advance only safe automatic Floor One steps."""
        from hollowstar import life_sim
        from hollowstar.scene import idle_pause

        run = self._active.get(run_id)
        if run is None:
            raise RunServiceError("load the run first")
        if not isinstance(run.context.get("life_world"), dict):
            raise RunServiceError("idle_tick currently requires an active Floor One social world")
        try:
            budget = max(1, min(int(max_steps), 8))
        except (TypeError, ValueError):
            raise RunServiceError("max_steps must be an integer between 1 and 8")

        events = []
        for _ in range(budget):
            public = life_sim.view(run)
            pause = idle_pause(public)
            if pause:
                return {"event": {"type": "idle_paused", "pause": pause,
                                   "steps": len(events), "events": events}, "state": public}
            room = public.get("room", {})
            exits = room.get("exits", {}) if isinstance(room, dict) else {}
            destination = next(iter(exits.values()), None) if isinstance(exits, dict) else None
            action = {"type": "move", "destination": destination} if destination else {
                "type": "world_tick", "elapsed_seconds": 60,
            }
            outcome = self._transition(run_id, lambda candidate, selected=action: life_sim.act(candidate, selected),
                                       action_label="idle_tick")
            events.append(copy.deepcopy(outcome.get("event", {})))
        return {"event": {"type": "idle_advanced", "steps": len(events), "events": events},
                "state": self.observe(run_id)}

    def auto_travel(self, run_id: str, *, destination: str = "well",
                    max_steps: int = 4, enter_descent: bool = False) -> dict:
        """Advance an authored public route through Floor One and save it."""
        from hollowstar import life_sim
        run = self._active.get(run_id)
        if run is None:
            raise RunServiceError("load the run first")
        if not isinstance(run.context.get("life_world"), dict):
            raise RunServiceError("auto_travel currently requires an active Floor One social world")
        if not isinstance(destination, str) or not destination.strip():
            raise RunServiceError("destination must be a non-empty location")
        try:
            budget = max(1, min(int(max_steps), 8))
        except (TypeError, ValueError):
            raise RunServiceError("max_steps must be an integer between 1 and 8")

        def transition(candidate):
            world = candidate.context["life_world"]
            locations = world["locations"]
            target = destination.strip().lower()
            if target not in locations:
                raise RunServiceError("destination is not an authored Floor One location")
            start = world["player"]["location"]
            queue = [(start, [])]
            seen = {start}
            path = None
            while queue:
                current, route = queue.pop(0)
                if current == target:
                    path = route
                    break
                for next_location in locations[current].get("exits", []):
                    if next_location not in seen:
                        seen.add(next_location)
                        queue.append((next_location, route + [next_location]))
            if path is None:
                raise RunServiceError("destination is not reachable from the current location")
            selected = path[:budget]
            events = []
            for next_location in selected:
                events.append(life_sim.act(candidate, {"type": "move", "destination": next_location})["event"])
            world = candidate.context["life_world"]
            world["travel"] = {"active": True, "mode": "auto", "animation": "travel",
                                "destination": target, "path": selected,
                                "steps": len(selected), "reached": world["player"]["location"] == target}
            descent = None
            if enter_descent and world["player"]["location"] == target:
                descent_result = life_sim.act(candidate, {"type": "descend"})
                descent = descent_result["event"]
                if candidate.context.get("scenario") == "reliquary_city":
                    from hollowstar import dungeon
                    candidate.context["city_world"] = candidate.context.pop("life_world")
                    dungeon_result = dungeon.start(candidate)
                    dungeon_result["descent"] = descent
                    return dungeon_result
            event = {"type": "auto_travel_advanced", "destination": target,
                     "path": selected, "reached": world["player"]["location"] == target,
                     "animation": "travel", "events": events}
            if descent:
                event["descent"] = descent
            return {"event": event, "state": life_sim.view(candidate)}

        return self._transition(run_id, transition, action_label="auto_travel")

    def sandbox_release(self, run_id: str) -> dict:
        """Explicitly end a D&D sandbox run so it stops holding the one-active
        slot ``sandbox_start`` enforces. Covers the case a prior session's
        sandbox run was abandoned (browser closed, host restarted) without a
        party wipe or gate-clear ever setting its status off ``active`` --
        without this, that stale run blocks every future sandbox_start
        forever. Writes a finished_record the same way a normal sandbox
        conclusion does, so prestige accounting sees it exactly once."""
        from hollowstar import sandbox
        self._path_for(run_id)
        run = self._active.get(run_id)
        if run is None:
            try:
                run = resume_run(self._path_for(run_id), expected_run_id=run_id)
            except RunStateError as exc:
                raise RunServiceError(str(exc)) from exc
        state = run.context.get("sandbox")
        if not isinstance(state, dict):
            raise RunServiceError(f"run has no D&D sandbox state to release: {run_id}")
        if state.get("status") == "active":
            state["status"] = "abandoned"
            if not state.get("finished_record"):
                record = sandbox.finished_record(run, run_id)
                self.finished_root.mkdir(parents=True, exist_ok=True)
                target = self.finished_root / f"{run_id}.json"
                atomic_json(target, record)
                state["finished_record"] = str(target)
            _save_run(run, run_id, self._path_for(run_id))
            if run_id in self._active:
                self._active[run_id] = run
        if self._active_sandbox_run_id == run_id:
            self._active_sandbox_run_id = None
        return {"run_id": run_id, "status": state.get("status")}

    def sandbox_start(self, run_id: str) -> dict:
        from hollowstar import sandbox
        current = self._active_sandbox_run_id
        if current and current != run_id:
            other = self._active.get(current)
            if other is not None and isinstance(other.context.get("sandbox"), dict) \
                    and other.context["sandbox"].get("status") == "active":
                raise RunServiceError(f"one active D&D sandbox run is already loaded: {current}")
        for path in self.run_root.glob("*.json") if self.run_root.exists() else []:
            if path.stem == run_id:
                continue
            try:
                other = resume_run(path, expected_run_id=path.stem)
            except RunStateError:
                continue
            other_sandbox = other.context.get("sandbox")
            if isinstance(other_sandbox, dict) and other_sandbox.get("status") == "active":
                raise RunServiceError(f"one active D&D sandbox run is already saved: {path.stem}")
        result = self._transition(run_id, sandbox.start, action_label="sandbox_start")
        self._active_sandbox_run_id = run_id
        return result

    def forge_start(self, run_id: str) -> dict:
        """Enter a placeless Forge threshold from an authored module fixture."""
        run = self._active.get(run_id)
        if run is None:
            raise RunServiceError("load the run first")
        if run.context.get("host_mode") != "FORGE":
            raise RunServiceError("Forge runs require an explicit FORGE boot")
        module = run.context.get("module")
        entry_fixture = module.get("entry_fixture") if isinstance(module, dict) else None
        if not isinstance(entry_fixture, dict) or not isinstance(entry_fixture.get("fixture_id"), str) \
                or not entry_fixture["fixture_id"].strip():
            raise RunServiceError("Forge requires an authored module entry fixture")
        if "forge" in run.context:
            if isinstance(run.context.get("dungeon"), dict):
                from hollowstar import dungeon
                event = self._forge_readout(run, "forge_resumed", already_started=True)["event"]
                return {"event": event, "state": dungeon.view(run)}
            return self._forge_readout(run, "forge_resumed", already_started=True)
        run.context["forge"] = {
            "schema": "hollow-star-forge-threshold-1",
            "status": "active",
            "fixture": entry_fixture["fixture_id"],
            "location": None,
            "chronology": None,
            "dialogue": None,
            "events": [],
            "receipt": None,
        }
        # Forge is a runtime, not only a receipt. An authored module enters the
        # ordinary dungeon engine; the Forge wrapper controls promotion and
        # canon boundaries without substituting the generic tavern sandbox.
        from hollowstar import dungeon
        world = self._transition(run_id, dungeon.start, action_label="forge_start")
        run = self._active[run_id]
        result = self._forge_readout(run, "forge_started")
        result["event"]["evidence"]["world_started"] = True
        result["event"]["world"] = world.get("event")
        result["state"] = world.get("state")
        if self.durable_saves:
            _save_run(run, run_id, self._path_for(run_id))
        return result

    @staticmethod
    def _forge_readout(run, event_type: str, *, already_started: bool = False) -> dict:
        forge = run.context["forge"]
        dungeon_state = run.context.get("dungeon")
        location = None
        if isinstance(dungeon_state, dict):
            location = f"{dungeon_state.get('floor')}:{dungeon_state.get('room')}"
        event = {
            "type": event_type,
            "fixture": forge["fixture"],
            "status": forge["status"],
            "evidence": {
                # A Forge run with a world is no longer placeless; it stays
                # non-canon either way, which is the guarantee that matters.
                "placeless": location is None,
                "non_canon": True,
                "already_started": already_started,
            },
        }
        state = {"schema": forge["schema"], "status": forge["status"],
                 "fixture": forge["fixture"], "location": location,
                 "chronology": None, "dialogue": None,
                 "events": copy.deepcopy(forge["events"]),
                 "receipt": copy.deepcopy(forge.get("receipt"))}
        return {"event": event, "state": state}

    def _forge_transition(self, run_id: str, action: dict, *, player_intent: str | None = None) -> dict:
        run = self._active.get(run_id)
        if run is None:
            raise RunServiceError("load the run first")
        forge = run.context["forge"]
        if forge["status"] != "active":
            raise RunServiceError("Forge threshold has ended")
        kind = str(action.get("type", "")).lower()
        if kind in {"observe", "inspect", "threshold"}:
            event = self._forge_readout(run, "forge_observation")["event"]
        elif kind in {"complete", "promote_candidate", "resolve"}:
            forge["status"] = "completed"
            forge["receipt"] = {
                "schema": "hollow-star-forge-candidate-1",
                "status": "review_only",
                "fixture": forge["fixture"],
                "canon_candidate": True,
                "location": (f"{run.context['dungeon'].get('floor')}:{run.context['dungeon'].get('room')}"
                             if isinstance(run.context.get("dungeon"), dict) else None),
                "chronology": None,
                "dialogue": None,
                "corpus_write": False,
                "promotion": "requires explicit Corey promotion of named results",
            }
            event = {"type": "forge_completed", "receipt": copy.deepcopy(forge["receipt"]),
                     "evidence": {"bound_within_run": True, "review_only": True}}
        elif kind in {"escape", "leave"}:
            forge["status"] = "escaped"
            event = {"type": "forge_escaped", "fixture": forge["fixture"],
                     "evidence": {"bound_within_run": True, "review_only": True}}
        else:
            raise RunServiceError("Forge threshold supports observe, complete, or escape")
        if player_intent:
            event["player_intent"] = player_intent
        forge["events"].append(copy.deepcopy(event))
        if self.durable_saves:
            _save_run(run, run_id, self._path_for(run_id))
        return {"event": event, "state": self._forge_readout(run, "forge_state")["state"]}

    def sandbox_debug(self, run_id: str) -> dict:
        from hollowstar import sandbox
        self._path_for(run_id)
        run = self._active.get(run_id)
        if run is None:
            try:
                run = resume_run(self._path_for(run_id), expected_run_id=run_id)
            except RunStateError as exc:
                raise RunServiceError(str(exc)) from exc
        return {"debug_readout": sandbox.view(run, debug=True),
                "warning": "private debug state; do not send this payload to the narrator"}

    def branch(self, run_id: str, new_run_id: str) -> RunSummary:
        """Copy a saved sandbox state into an isolated alternate run."""
        self._path_for(new_run_id)
        target = self._path_for(new_run_id)
        if target.exists():
            raise RunServiceError(f"run already exists: {new_run_id}")
        source = self._active.get(run_id)
        if source is None:
            source = resume_run(self._path_for(run_id), expected_run_id=run_id)
        if not isinstance(source.context.get("sandbox"), dict):
            raise RunServiceError("branching is currently available only for D&D sandbox runs")
        candidate = copy.deepcopy(source)
        candidate.context["sandbox"]["branch_parent"] = run_id
        candidate.context["sandbox"]["branch_id"] = new_run_id
        _save_run(candidate, new_run_id, target)
        return summarize(new_run_id, candidate)

    def finished_runs(self) -> list[str]:
        if not self.finished_root.exists():
            return []
        return sorted(path.stem for path in self.finished_root.glob("*.json") if path.name != "prestige.json")

    def sandbox_prestige(self) -> dict:
        total = {"flat": 0, "bonus": 0, "total": 0, "runs": 0}
        for path in sorted(self.finished_root.glob("*.json")) if self.finished_root.exists() else []:
            try:
                data = __import__("json").loads(path.read_text(encoding="utf-8"))
            except (OSError, UnicodeError, ValueError):
                continue
            if data.get("record_type") != "finished_run":
                continue
            award = data.get("rewards") or {}
            total["flat"] += int(award.get("flat", 0))
            total["bonus"] += int(award.get("bonus", 0))
            total["total"] += int(award.get("total", 0))
            total["runs"] += 1
        return total

    def _transition(self, run_id, transition, *, action_label: str | None = None,
                    player_intent: str | None = None, include_state: bool = True):
        from hollowstar import dungeon
        from hollowstar import sandbox
        from hollowstar import life_sim
        from hollowstar.tactical import ActionError
        self._path_for(run_id)
        original = self._active.get(run_id)
        if original is None:
            raise RunServiceError("load the run first")
        sandbox_transition = isinstance(original.context.get("sandbox"), dict) or action_label == "sandbox_start"
        life_transition = isinstance(original.context.get("life_world"), dict) or action_label == "life_world_start"
        candidate = dungeon.clone_for_transition(original)
        try:
            transition_result = transition(candidate)
            # The D&D fixture historically returned its own {event, state}
            # envelope. Normalize that here so callers receive one envelope,
            # while retaining the transition event as the top-level event.
            if (isinstance(transition_result, dict)
                    and isinstance(transition_result.get("event"), dict)
                    and set(transition_result) <= {"event", "state"}):
                event = transition_result["event"]
            else:
                event = transition_result
            if isinstance(event, dict):
                from hollowstar.commentary import attach
                event = attach(candidate, action_label or "transition", event)
            if isinstance(event, dict) and "evidence" not in event:
                event["evidence"]={"action":action_label or "transition",
                                    "state_committed":True,
                                    "source":"authoritative RunService fallback"}
            if "dungeon" in candidate.context:
                record = copy.deepcopy(event)
                if player_intent is not None:
                    record["player_intent"] = player_intent
                candidate.context["dungeon"]["events"].append(record)
            if sandbox_transition and isinstance(candidate.context.get("sandbox"), dict):
                if candidate.context["sandbox"].get("status") != "active" and not candidate.context["sandbox"].get("finished_record"):
                    record = sandbox.finished_record(candidate, run_id)
                    self.finished_root.mkdir(parents=True, exist_ok=True)
                    target = self.finished_root / f"{run_id}.json"
                    atomic_json(target, record)
                    candidate.context["sandbox"]["finished_record"] = str(target)
            visible = (sandbox.view(candidate) if include_state and sandbox_transition and "sandbox" in candidate.context
                       else life_sim.view(candidate) if include_state and life_transition and "life_world" in candidate.context
                       else dungeon.view(candidate) if include_state and "dungeon" in candidate.context else None)
            if self.durable_saves:
                _save_run(candidate, run_id, self._path_for(run_id))
        except (ActionError, ValueError, TypeError, IndexError, KeyError) as exc:
            raise RunServiceError(str(exc)) from exc
        self._active[run_id] = candidate
        return {"event": event, "state": visible}

    def observe(self, run_id: str) -> dict:
        from hollowstar import dungeon
        from hollowstar import sandbox
        self._path_for(run_id)
        run = self._active.get(run_id)
        if run is None:
            try:
                run = resume_run(self._path_for(run_id), expected_run_id=run_id)
            except RunStateError as exc:
                raise RunServiceError(str(exc)) from exc
        if isinstance(run.context.get("sandbox"), dict):
            return sandbox.view(run)
        if isinstance(run.context.get("life_world"), dict):
            from hollowstar import life_sim
            return life_sim.view(run)
        if isinstance(run.context.get("forge"), dict):
            return self._forge_readout(run, "forge_observation", already_started=True)["state"]
        return dungeon.view(run)

    def content_catalog(self, run_id: str | None = None) -> dict:
        """Return source-linked content, scoped to a run's visible party when possible."""
        from hollowstar.content_registry import entries, load_registry
        run = self._active.get(run_id) if run_id else None
        if run is not None:
            registry = run.context.get("content_registry") or load_registry()
            owners={actor.name.lower() for actor in run.party if actor.name.lower() in {"doran","wren"}}
            rows=entries(registry, owners=owners)
        else:
            registry=load_registry()
            rows=entries(registry)
        return {"registry_version":registry["registry_version"],"entries":rows,
                "deferred_rules":copy.deepcopy(registry.get("deferred_rules",[])),
                "scope":"selected party" if run is not None else "registry"}

    def register_ruling(self, run_id: str, ruling: dict) -> dict:
        from hollowstar.spells import validate_ruling
        spec = validate_ruling(ruling)
        def register(run):
            identifier = spec['name'] + '@' + spec['edition']
            run.context.setdefault('spell_rulings', {})[identifier] = spec
            return {'type': 'ruling_registered', 'id': identifier, 'ruling': spec}
        return self._transition(run_id, register)
