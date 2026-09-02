"""
tests/test_constants.py
Tests for utils/constants.py: paths, dir creation, resource_path helper.
"""
import os
import sys
import unittest


class TestConstants(unittest.TestCase):
    def test_app_data_dir_defined(self):
        from utils.constants import APP_DATA_DIR
        self.assertTrue(len(APP_DATA_DIR) > 0)

    def test_app_data_dir_exists(self):
        from utils.constants import APP_DATA_DIR
        self.assertTrue(os.path.isdir(APP_DATA_DIR))

    def test_templates_dir_exists(self):
        from utils.constants import TEMPLATES_DIR
        self.assertTrue(os.path.isdir(TEMPLATES_DIR))

    def test_datasets_dir_exists(self):
        from utils.constants import DATASETS_DIR
        self.assertTrue(os.path.isdir(DATASETS_DIR))

    def test_recovery_dir_exists(self):
        from utils.constants import RECOVERY_DIR
        self.assertTrue(os.path.isdir(RECOVERY_DIR))

    def test_app_data_in_appdata(self):
        from utils.constants import APP_DATA_DIR
        app_data_env = os.environ.get("APPDATA", "")
        self.assertTrue(APP_DATA_DIR.startswith(app_data_env))

    def test_dirs_are_children_of_app_data(self):
        from utils.constants import APP_DATA_DIR, TEMPLATES_DIR, DATASETS_DIR, RECOVERY_DIR
        for d in [TEMPLATES_DIR, DATASETS_DIR, RECOVERY_DIR]:
            self.assertTrue(d.startswith(APP_DATA_DIR))

    def test_resource_path_returns_string(self):
        from utils.constants import resource_path
        result = resource_path("some/asset.png")
        self.assertIsInstance(result, str)

    def test_resource_path_in_dev_mode(self):
        from utils.constants import resource_path
        # In dev mode (no _MEIPASS), path should be relative to project root
        self.assertIn("some", resource_path("some/asset.png"))
        self.assertIn("asset.png", resource_path("some/asset.png"))

    def test_resource_path_not_empty(self):
        from utils.constants import resource_path
        result = resource_path("utils/constants.py")
        self.assertGreater(len(result), 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
