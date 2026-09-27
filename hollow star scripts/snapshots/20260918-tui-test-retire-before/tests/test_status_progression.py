import io
import tempfile
from pathlib import Path

from hollowstar.host import HSRHost
from hollowstar.session_screen import SessionScreen


def test_terminal_status_includes_persistent_progression_for_active_party():
    with tempfile.TemporaryDirectory(prefix="hsr-status-") as temp:
        host = HSRHost.from_options(data_root=Path(temp) / ".local")
        screen = SessionScreen(host, io.StringIO(), io.StringIO())
        screen.request("boot", mode="DESIGN")
        screen.request("create_run", run_id="status-run", seed="status-seed",
                       party=["divine:Doran"], opposition=["Townsperson"])
        screen.run_id = "status-run"
        text = screen.status()
        assert "Meta divine:Doran" in text
        assert "Rank 1" in text
