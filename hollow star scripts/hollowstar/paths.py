"""Path and configuration boundary for the local Hollow Star host.

The story corpus and the executable HSR project deliberately live beside one
another.  This module makes that relationship explicit without making the
engine depend on the process' current working directory.
"""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from pathlib import Path, PureWindowsPath


class HostPathError(ValueError):
    """Raised when host paths are missing or escape their allowed roots."""


DEFAULT_CONFIG = Path(__file__).resolve().parents[1] / "host_config.json"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@dataclass(frozen=True)
class HostConfig:
    schema_version: str
    rules_profile: str
    paths: dict[str, str]
    local_pc_required: bool
    local_desktop_root: str
    local_workspace_prefix: str
    modes: dict[str, str]


@dataclass(frozen=True)
class HostPaths:
    """Resolved paths for one Court workspace and one HSR data root."""

    workspace_root: Path
    hsr_root: Path
    corpus_root: Path
    content_root: Path
    snapshot_path: Path
    handshake_path: Path
    data_root: Path
    run_root: Path
    profile_root: Path
    config_path: Path
    rules_profile: str
    local_pc_required: bool
    local_desktop_root: Path
    local_workspace_prefix: str
    modes: dict[str, str]
    local_desktop_root_declared: str = ""

    @staticmethod
    def _resolved(path: Path) -> Path:
        return path.expanduser().resolve()

    def assert_workspace_layout(self) -> None:
        required = {
            "workspace root": self.workspace_root,
            "HSR root": self.hsr_root,
            "corpus root": self.corpus_root,
            "content root": self.content_root,
            "snapshot": self.snapshot_path,
            "config": self.config_path,
        }
        missing = [label for label, path in required.items() if not path.exists()]
        if missing:
            raise HostPathError("missing host path(s): " + ", ".join(missing))

    @property
    def _declared_desktop_root(self) -> str:
        """The Desktop root exactly as configured, never host-resolved.

        ``local_desktop_root`` is a ``Path``, so on a non-Windows host the
        configured ``C:/...`` value is not recognised as absolute and gets
        joined onto the current directory.  Comparisons and error messages
        must use the declared string instead.
        """

        return self.local_desktop_root_declared or str(self.local_desktop_root)

    def _is_approved_windows_workspace(self, value: str) -> bool:
        """True when a Windows path is a direct, correctly named Desktop child."""

        if not value:
            return False
        candidate = PureWindowsPath(value)
        expected = PureWindowsPath(self._declared_desktop_root)
        if candidate.parent != expected:
            return False
        return candidate.name.lower().startswith(self.local_workspace_prefix.lower())

    def _bridge_identity_report(self) -> dict[str, object]:
        """Decide whether a non-Windows mount *is* the approved workspace.

        Path shape cannot answer this question off Windows: a device-bridge
        mount of the real folder and a read-only project mirror of it look
        alike.  The handshake can answer it.  It records the Windows
        workspace a passing local-check ran in and binds SHA-256 digests of
        the config and snapshot as they were at that moment, so a mount is
        accepted only when it carries the same folder name, still hashes to
        the recorded digests, and can actually be written to.  A stale
        mirror fails on the digests; a read-only mount fails on the write
        probe.
        """

        detail: dict[str, object] = {"proven": False}
        try:
            raw = json.loads(self.handshake_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError):
            detail["reason"] = "handshake is missing or unreadable"
            return detail
        if not isinstance(raw, dict) or raw.get("result") != "pass":
            detail["reason"] = "handshake does not record a passing local-check"
            return detail

        declared = str(raw.get("validated_workspace_root", ""))
        detail["validated_workspace_root"] = declared
        if not self._is_approved_windows_workspace(declared):
            detail["reason"] = "handshake was not validated in an approved Desktop workspace"
            return detail
        if PureWindowsPath(declared).name.lower() != self.workspace_root.name.lower():
            detail["reason"] = "mounted folder name does not match the handshake"
            return detail

        recorded = raw.get("artifact_hashes")
        if not isinstance(recorded, dict):
            detail["reason"] = "handshake records no artifact hashes"
            return detail
        for label, path in (
            ("config_sha256", self.config_path),
            ("snapshot_sha256", self.snapshot_path),
        ):
            try:
                actual = _sha256(path)
            except OSError:
                detail["reason"] = f"cannot read {path.name} to verify {label}"
                return detail
            if actual != recorded.get(label):
                detail["reason"] = f"{label} does not match the handshake"
                return detail

        writable = self.data_root if self.data_root.exists() else self.workspace_root
        if not os.access(writable, os.W_OK):
            detail["reason"] = f"mount is not writable at {writable}"
            return detail

        detail["proven"] = True
        detail["reason"] = "handshake identity proven against live bytes"
        return detail

    def local_location_report(self) -> dict[str, object]:
        """Report whether this process may run against this workspace.

        Two shapes are approved.  A native Windows workspace directly
        beneath the configured Desktop root is approved by its path.  A
        device-bridge mount of that same workspace cannot have that shape,
        so it is approved only by proving its identity through the
        handshake.  Everything else -- UNC paths, project mirrors, stray
        copies -- still fails closed.
        """

        workspace = self.workspace_root.resolve()
        desktop = self._declared_desktop_root
        is_unc = workspace.anchor.startswith("\\\\")
        report: dict[str, object] = {
            "required": self.local_pc_required,
            "approved": False,
            "via": "none",
            "workspace_root": str(workspace),
            "expected_desktop_root": desktop,
            "workspace_name_prefix": self.local_workspace_prefix,
            "is_unc": is_unc,
        }

        if is_unc:
            report["reason"] = "UNC/network path is not an approved local PC workspace"
            return report

        if self._is_approved_windows_workspace(str(workspace)):
            report["approved"] = True
            report["via"] = "native"
            report["reason"] = "approved local OneDrive Desktop workspace"
            return report

        bridge = self._bridge_identity_report()
        report["bridge_identity"] = bridge
        if bridge["proven"]:
            report["approved"] = True
            report["via"] = "bridge"
            report["reason"] = "approved device-bridge mount of the local workspace"
            return report

        report["reason"] = (
            f"workspace is neither directly beneath {desktop} nor a verified "
            f"bridge mount: {bridge['reason']}"
        )
        return report

    def assert_local_pc_workspace(self) -> dict[str, object]:
        report = self.local_location_report()
        if self.local_pc_required and not report["approved"]:
            raise HostPathError(
                "HSR requires the local ACore OneDrive Desktop workspace: "
                + str(report["workspace_root"])
                + "; "
                + str(report["reason"])
            )
        return report

    def assert_state_path(self, path: Path | str) -> Path:
        """Allow state writes only below the configured data root."""

        target = self._resolved(Path(path))
        try:
            target.relative_to(self.data_root)
        except ValueError as exc:
            raise HostPathError(
                f"state path escapes data root: {target}; allowed root is {self.data_root}"
            ) from exc
        try:
            target.relative_to(self.corpus_root)
        except ValueError:
            return target
        raise HostPathError(f"state path is inside the read-only corpus: {target}")

    def ensure_state_dirs(self) -> None:
        """Create only disposable local state directories."""

        self.data_root.mkdir(parents=True, exist_ok=True)
        self.run_root.mkdir(parents=True, exist_ok=True)
        self.profile_root.mkdir(parents=True, exist_ok=True)


def load_config(path: Path | str | None = None) -> HostConfig:
    config_path = Path(path) if path else DEFAULT_CONFIG
    try:
        raw = json.loads(config_path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise HostPathError(f"host config does not exist: {config_path}") from exc
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise HostPathError(f"host config is not valid JSON: {config_path}") from exc

    if not isinstance(raw, dict):
        raise HostPathError("host config root must be an object")
    if raw.get("schema_version") != "hollow-star-host-config-1":
        raise HostPathError("host config schema mismatch")
    paths = raw.get("paths")
    if not isinstance(paths, dict):
        raise HostPathError("host config has no paths object")
    required = {
        "corpus_dir",
        "hsr_dir",
        "content_dir",
        "snapshot",
        "handshake",
        "data_dir",
        "runs_dir",
        "profiles_dir",
    }
    if not required <= set(paths):
        raise HostPathError("host config is missing one or more required paths")
    modes = raw.get("modes")
    if not isinstance(modes, dict) or not modes:
        raise HostPathError("host config has no modes object")
    return HostConfig(
        schema_version=raw["schema_version"],
        rules_profile=str(raw.get("rules_profile", "2014_5e_hsr_overlay")),
        paths={str(k): str(v) for k, v in paths.items()},
        local_pc_required=bool(raw.get("local_pc_required", True)),
        local_desktop_root=str(
            raw.get("local_desktop_root", r"C:\Users\ACore\OneDrive\Desktop")
        ),
        local_workspace_prefix=str(raw.get("local_workspace_prefix", "Soliera and Sera")),
        modes={str(k).upper(): str(v).lower() for k, v in modes.items()},
    )


def resolve_paths(
    workspace_root: Path | str | None = None,
    data_root: Path | str | None = None,
    config_path: Path | str | None = None,
) -> HostPaths:
    """Resolve all host paths from a workspace root and optional overrides."""

    config_file = Path(config_path) if config_path else DEFAULT_CONFIG
    config = load_config(config_file)
    hsr_root_from_file = config_file.resolve().parent
    default_workspace = hsr_root_from_file.parent
    workspace = Path(workspace_root).expanduser().resolve() if workspace_root else default_workspace

    def rooted(value: str) -> Path:
        candidate = Path(value).expanduser()
        return (candidate if candidate.is_absolute() else workspace / candidate).resolve()

    hsr_root = rooted(config.paths["hsr_dir"])
    corpus_root = rooted(config.paths["corpus_dir"])
    content_root = rooted(config.paths["content_dir"])
    snapshot_path = rooted(config.paths["snapshot"])
    handshake_path = rooted(config.paths["handshake"])
    configured_data = rooted(config.paths["data_dir"])
    data = Path(data_root).expanduser().resolve() if data_root else configured_data
    run_root = data / Path(config.paths["runs_dir"]).name
    profile_root = data / Path(config.paths["profiles_dir"]).name

    return HostPaths(
        workspace_root=workspace,
        hsr_root=hsr_root,
        corpus_root=corpus_root,
        content_root=content_root,
        snapshot_path=snapshot_path,
        handshake_path=handshake_path,
        data_root=data,
        run_root=run_root,
        profile_root=profile_root,
        config_path=config_file.resolve(),
        rules_profile=config.rules_profile,
        local_pc_required=config.local_pc_required,
        local_desktop_root=Path(config.local_desktop_root).expanduser().resolve(),
        local_workspace_prefix=config.local_workspace_prefix,
        modes=config.modes,
        local_desktop_root_declared=config.local_desktop_root,
    )
