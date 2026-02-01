import time
import unittest

from ascii_stream_engine.core.config import EngineConfig
from ascii_stream_engine.core.engine import StreamEngine
from ascii_stream_engine.core.pipeline import AnalyzerPipeline, FilterPipeline
from ascii_stream_engine.core.types import RenderFrame


class DummySource:
    def __init__(self, frame=1):
        self.frame = frame
        self.opened = False

    def open(self) -> None:
        self.opened = True

    def read(self):
        return self.frame

    def close(self) -> None:
        self.opened = False


class DummyRenderer:
    def __init__(self):
        self.last_frame = None

    def output_size(self, config):
        return (10, 10)

    def render(self, frame, config, analysis=None):
        self.last_frame = frame
        return RenderFrame(image=object(), text="x", lines=["x"])


class DummySink:
    def __init__(self):
        self.count = 0
        self.output_size = None

    def open(self, config, output_size):
        self.output_size = output_size

    def write(self, frame):
        self.count += 1

    def close(self):
        pass


class DummyAnalyzer:
    name = "dummy"

    def __init__(self, enabled=True):
        self.enabled = enabled

    def analyze(self, frame, config):
        return {"value": frame}


class DummyFilter:
    name = "plus_one"

    def __init__(self, enabled=True):
        self.enabled = enabled

    def apply(self, frame, config, analysis=None):
        return frame + 1


class TestStreamEngine(unittest.TestCase):
    def test_engine_processes_frames(self) -> None:
        config = EngineConfig(fps=30, frame_buffer_size=0, sleep_on_empty=0.001)
        source = DummySource(frame=1)
        renderer = DummyRenderer()
        sink = DummySink()
        analyzers = AnalyzerPipeline([DummyAnalyzer()])
        filters = FilterPipeline([DummyFilter()])

        engine = StreamEngine(
            source=source,
            renderer=renderer,
            sink=sink,
            config=config,
            analyzers=analyzers,
            filters=filters,
        )
        engine.start()
        time.sleep(0.05)
        engine.stop()

        self.assertGreaterEqual(sink.count, 1)
        self.assertEqual(renderer.last_frame, 2)
        analysis = engine.get_last_analysis()
        self.assertIn("dummy", analysis)
        self.assertIn("timestamp", analysis)


if __name__ == "__main__":
    unittest.main()
