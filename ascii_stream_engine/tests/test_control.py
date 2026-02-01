import unittest
from unittest.mock import patch

from ascii_stream_engine.core.config import EngineConfig
from ascii_stream_engine.tests import has_module


class DummyEngine:
    def __init__(self):
        self._config = EngineConfig()
        self.filters = []

    def get_config(self):
        return self._config

    def update_config(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self._config, key, value)


class TestNotebookControl(unittest.TestCase):
    def test_build_control_panel_imports(self) -> None:
        from ascii_stream_engine.control.notebook_api import build_control_panel

        engine = DummyEngine()

        if not has_module("ipywidgets"):
            with self.assertRaises(ImportError):
                build_control_panel(engine)
            return

        if not has_module("IPython"):
            with self.assertRaises(ImportError):
                build_control_panel(engine)
            return

        with patch("IPython.display.display") as _:
            panel = build_control_panel(engine)
        self.assertIn("config", panel)
        self.assertIn("filters", panel)


if __name__ == "__main__":
    unittest.main()
