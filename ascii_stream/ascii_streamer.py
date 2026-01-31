import subprocess
import threading
import time
from typing import Optional

import cv2

from .base import Streamer
from .config import AsciiStreamConfig
from .image_processor import AsciiImageProcessor


def _start_ffmpeg(out_w: int, out_h: int, fps: int, cfg: AsciiStreamConfig) -> subprocess.Popen:
    cmd = [
        "ffmpeg",
        "-loglevel",
        "error",
        "-f",
        "rawvideo",
        "-pix_fmt",
        "rgb24",
        "-s",
        f"{out_w}x{out_h}",
        "-framerate",
        str(fps),
        "-i",
        "-",
        "-an",
        "-c:v",
        "mpeg1video",
        "-b:v",
        cfg.bitrate,
        "-f",
        "mpegts",
        f"udp://{cfg.host}:{cfg.port}?pkt_size={cfg.pkt_size}",
    ]
    return subprocess.Popen(cmd, stdin=subprocess.PIPE)


class AsciiStreamer(Streamer):
    def __init__(
        self,
        config: Optional[AsciiStreamConfig] = None,
        image_processor: Optional[AsciiImageProcessor] = None,
    ) -> None:
        super().__init__()
        self._config = config or AsciiStreamConfig()
        self._config_lock = threading.Lock()
        self._image_processor = image_processor or AsciiImageProcessor()

    def get_config(self) -> AsciiStreamConfig:
        with self._config_lock:
            return AsciiStreamConfig(**vars(self._config))

    def update_config(self, **kwargs) -> None:
        with self._config_lock:
            for key, value in kwargs.items():
                if not hasattr(self._config, key):
                    raise ValueError(f"Parametro desconocido: {key}")
                setattr(self._config, key, value)

    def get_processor(self) -> AsciiImageProcessor:
        return self._image_processor

    def set_processor(self, processor: AsciiImageProcessor) -> None:
        self._image_processor = processor

    def start(self, camera_index: int = 0) -> None:
        super().start(camera_index=camera_index)

    def _run(self, camera_index: int) -> None:
        cfg = self.get_config()
        out_w, out_h = self._image_processor.output_size(cfg)

        proc = _start_ffmpeg(out_w, out_h, cfg.fps, cfg)
        cap = cv2.VideoCapture(camera_index)
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

        last = time.perf_counter()
        try:
            while not self._stop_event.is_set():
                ret, frame = cap.read()
                if not ret:
                    time.sleep(0.01)
                    continue

                cfg = self.get_config()
                img = self._image_processor.render(frame, cfg)

                try:
                    if proc.stdin:
                        proc.stdin.write(img.tobytes())
                except (BrokenPipeError, OSError):
                    break

                target = 1.0 / max(1, int(cfg.fps))
                now = time.perf_counter()
                sleep = target - (now - last)
                if sleep > 0:
                    time.sleep(sleep)
                last = time.perf_counter()
        finally:
            cap.release()
            if proc.stdin:
                try:
                    proc.stdin.close()
                except Exception:
                    pass
            proc.wait()
