import json
import tempfile
import threading
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from unittest.mock import patch
import unittest

import hollowstar_web_server as web
from hollowstar.hosted_controls import HostedControls


class HostedControlsTests(unittest.TestCase):
  def test_named_credentials_and_single_controller_lease(self):
    with tempfile.TemporaryDirectory() as temp:
        controls = HostedControls(Path(temp) / "hosted.json")
        tokens = controls.provision()
        assert controls.authenticate("claude", tokens["claude"])[0]
        assert not controls.authenticate("gpt", tokens["claude"])[0]
        assert controls.lease("claude", "run-1", "acquire")[0]
        ok, code, _ = controls.lease("gpt", "run-1", "acquire")
        assert not ok and code == "HOSTED_LEASE_CONFLICT"
        assert controls.lease("claude", "run-1", "release")[0]


  def test_hosted_relay_rejects_forbidden_and_replays_without_engine_call(self):
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        controls = HostedControls(root / "hosted.json")
        tokens = controls.provision()
        with patch.object(web, "_hosted_controls", controls), patch.object(web, "_engine") as engine:
            with web.ThreadingHTTPServer(("127.0.0.1", 0), web.Handler) as server:
                thread = threading.Thread(target=server.serve_forever)
                thread.start()
                try:
                    url = f"http://127.0.0.1:{server.server_port}/api/hosted"
                    headers = {"Content-Type": "application/json", "X-HSR-Client": "claude", "Authorization": "Bearer " + tokens["claude"]}
                    forbidden = Request(url, data=json.dumps({"id": "same", "command": "shutdown"}).encode(), headers=headers)
                    try:
                        with urlopen(forbidden) as response:
                            payload = json.load(response)
                    except HTTPError as error:
                        payload = json.load(error)
                    assert payload["error"]["code"] == "HOSTED_COMMAND_FORBIDDEN"
                    assert not engine.called
                finally:
                    server.shutdown()
                    thread.join(timeout=5)


if __name__ == "__main__":
    unittest.main()
