import subprocess
import threading
import time
from dataclasses import dataclass
from typing import Optional

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

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


class AsciiStreamer:
    def __init__(self, config: Optional[AsciiStreamConfig] = None) -> None:
        self._config = config or AsciiStreamConfig()
        self._config_lock = threading.Lock()
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None

    def get_config(self) -> AsciiStreamConfig:
        with self._config_lock:
            return AsciiStreamConfig(**vars(self._config))

    def update_config(self, **kwargs) -> None:
        with self._config_lock:
            for key, value in kwargs.items():
                if not hasattr(self._config, key):
                    raise ValueError(f"Parametro desconocido: {key}")
                setattr(self._config, key, value)

    @property
    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def start(self, camera_index: int = 0) -> None:
        if self.is_running:
            return
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._run, args=(camera_index,), daemon=True
        )
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=2)

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


def _parse_args():
    import argparse

    parser = argparse.ArgumentParser(description="Stream ASCII por UDP con ffmpeg.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=1234)
    parser.add_argument("--grid-w", type=int, default=120)
    parser.add_argument("--grid-h", type=int, default=60)
    parser.add_argument("--fps", type=int, default=20)
    parser.add_argument("--invert", action="store_true")
    parser.add_argument("--contrast", type=float, default=1.2)
    parser.add_argument("--brightness", type=int, default=0)
    parser.add_argument("--charset", default="suave")
    parser.add_argument("--camera", type=int, default=0)
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    cfg = AsciiStreamConfig(
        grid_w=args.grid_w,
        grid_h=args.grid_h,
        fps=args.fps,
        invert=args.invert,
        contrast=args.contrast,
        brightness=args.brightness,
        charset=args.charset,
        host=args.host,
        port=args.port,
    )
    streamer = AsciiStreamer(cfg)
    streamer.start(camera_index=args.camera)
    try:
        while streamer.is_running:
            time.sleep(0.2)
    except KeyboardInterrupt:
        pass
    finally:
        streamer.stop()


if __name__ == "__main__":
    main()
