# HSR
The Hollow Star Reliquary is a dungeon designed by Gods for their friends and even citizens of their nations to experience.

## Cloud working copy: read before working

This is a **one-time working copy** of the HSR game, made to spend a block of Claude cloud credit on it. The master lives on Corey's PC (`C:\Users\ACore\OneDrive\Desktop\Soliera and Sera v9.0 - The Divine System`). After the credit is spent, work returns to the master.

- **HSR only.** Work in `hollow star scripts/`. `divine mythos set/` is the game's read-only corpus. The runtime points at it, so leave it untouched.
- **Work on a branch.** Claude Code on the web names each cloud session's branch automatically (e.g. `claude/adoring-gauss-u7bpaz`) rather than reusing a fixed `cloud-work` name — check `git branch --show-current` for the one in use. Corey copies changed files back into the master by hand. Nothing merges automatically.
- **Never copy back:** `hollow star scripts/host_config.json` (this copy sets `local_pc_required` to `false`) and anything under `.local/`.
- **Run the game tests:** `cd "hollow star scripts" && python tools/run_discovered_tests.py`. The location-guard tests (`test_bridge_gate`, `test_nonlocal_workspace_fails_closed`) are expected to fail here, since the guard is off.
- Master-side corpus tools, checkers and manifests are not in this repo.
