import subprocess
import threading
import time
from dataclasses import dataclass
from typing import Optional

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from .base import Streamer

ASCII_SETS = {
    "suave": " .:-=+*#%@",
    "denso": " .'`^\",:;Il!i~+_-?][}{1)(|\\/tfjrxnuvczXYUJCLQ0OZmwqpdbkhao*#MW&8%B@$",
}


@dataclass
class AsciiStreamConfig:
    grid_w: int = 120
    grid_h: int = 60
    fps: int = 20
    invert: bool = False
    contrast: float = 1.2
    brightness: int = 0
    charset: str = "suave"
    host: str = "127.0.0.1"
    port: int = 1234
    pkt_size: int = 1316
    bitrate: str = "1500k"


def _resolve_charset(name_or_charset: str) -> str:
    return ASCII_SETS.get(name_or_charset, name_or_charset)


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
    def __init__(self, config: Optional[AsciiStreamConfig] = None) -> None:
        super().__init__()
        self._config = config or AsciiStreamConfig()
        self._config_lock = threading.Lock()

    def get_config(self) -> AsciiStreamConfig:
        with self._config_lock:
            return AsciiStreamConfig(**vars(self._config))

    def update_config(self, **kwargs) -> None:
        with self._config_lock:
            for key, value in kwargs.items():
                if not hasattr(self._config, key):
                    raise ValueError(f"Parametro desconocido: {key}")
                setattr(self._config, key, value)

    def start(self, camera_index: int = 0) -> None:
        super().start(camera_index=camera_index)

    def _run(self, camera_index: int) -> None:
        cfg = self.get_config()
        font = ImageFont.load_default()
        bbox = font.getbbox("A")
        char_w = bbox[2] - bbox[0]
        char_h = bbox[3] - bbox[1]

        out_w = cfg.grid_w * char_w
        out_h = cfg.grid_h * char_h

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
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                if cfg.contrast != 1.0 or cfg.brightness != 0:
                    gray = cv2.convertScaleAbs(
                        gray, alpha=float(cfg.contrast), beta=int(cfg.brightness)
                    )
                if cfg.invert:
                    gray = 255 - gray

                small = cv2.resize(
                    gray, (cfg.grid_w, cfg.grid_h), interpolation=cv2.INTER_AREA
                )
                chars = _resolve_charset(cfg.charset)
                idx = (small / 255 * (len(chars) - 1)).astype(np.int32)

                img = Image.new("RGB", (out_w, out_h), color=(0, 0, 0))
                draw = ImageDraw.Draw(img)
                y = 0
                for row in idx:
                    line = "".join(chars[i] for i in row)
                    draw.text((0, y), line, fill=(255, 255, 255), font=font)
                    y += char_h

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
