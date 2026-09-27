import importlib.util
import os
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("hollowstar_app", ROOT / "hollowstar_app.py")
assert SPEC and SPEC.loader
hollowstar_app = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(hollowstar_app)


class LauncherGeometryTests(unittest.TestCase):
    def test_reference_4k_geometry_matches_measured_screenshot(self):
        geometry = hollowstar_app._launch_geometry((0, 0, 3839, 2159))
        self.assertEqual(geometry, hollowstar_app.WindowGeometry(3132, 1569, 423, 211))

    def test_geometry_scales_and_stays_inside_offset_work_area(self):
        geometry = hollowstar_app._launch_geometry((-1920, 40, 0, 1120))
        self.assertEqual(geometry.width, 1566)
        self.assertEqual(geometry.height, 785)
        self.assertGreaterEqual(geometry.left, -1920)
        self.assertGreaterEqual(geometry.top, 40)
        self.assertLessEqual(geometry.left + geometry.width, 0)
        self.assertLessEqual(geometry.top + geometry.height, 1120)

    def test_small_work_area_is_clamped_without_overflow(self):
        geometry = hollowstar_app._launch_geometry((0, 0, 1024, 600))
        self.assertEqual(geometry.width, 1024)
        self.assertEqual(geometry.height, 600)
        self.assertEqual((geometry.left, geometry.top), (0, 0))

    def test_chromium_command_receives_size_and_position(self):
        browser = Path("C:/Browser/msedge.exe")
        geometry = hollowstar_app.WindowGeometry(2089, 1047, 282, 141)
        with mock.patch.object(hollowstar_app.shutil, "which", return_value=str(browser)), \
             mock.patch.object(Path, "is_file", return_value=True):
            command = hollowstar_app._browser_command("http://127.0.0.1:8765/web/index.html", geometry)
        self.assertIn("--window-size=2089,1047", command)
        self.assertIn("--window-position=282,141", command)


if __name__ == "__main__":
    unittest.main()
