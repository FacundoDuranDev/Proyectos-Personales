import threading
from typing import Iterable, List, Optional

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from .config import AsciiStreamConfig
from .constants import resolve_charset
from .filters import ContrastBrightnessFilter, FrameFilter, GrayscaleFilter, InvertFilter


class AsciiImageProcessor:
    def __init__(
        self,
        filters: Optional[Iterable[FrameFilter]] = None,
        font: Optional[ImageFont.ImageFont] = None,
    ) -> None:
        self._filters: List[FrameFilter] = list(filters) if filters is not None else [
            GrayscaleFilter(),
            ContrastBrightnessFilter(),
            InvertFilter(),
        ]
        self._filters_lock = threading.Lock()
        self._font = font or ImageFont.load_default()
        bbox = self._font.getbbox("A")
        self._char_w = bbox[2] - bbox[0]
        self._char_h = bbox[3] - bbox[1]

    @property
    def filters(self) -> List[FrameFilter]:
        with self._filters_lock:
            return list(self._filters)

    def set_filters(self, filters: Iterable[FrameFilter]) -> None:
        with self._filters_lock:
            self._filters = list(filters)

    def add_filter(self, filter_obj: FrameFilter) -> None:
        with self._filters_lock:
            self._filters.append(filter_obj)

    def output_size(self, config: AsciiStreamConfig) -> tuple[int, int]:
        return config.grid_w * self._char_w, config.grid_h * self._char_h

    def render(self, frame: np.ndarray, config: AsciiStreamConfig) -> Image.Image:
        with self._filters_lock:
            filters = list(self._filters)

        processed = frame
        for filter_obj in filters:
            processed = filter_obj.apply(processed, config)

        if processed.ndim == 3:
            processed = cv2.cvtColor(processed, cv2.COLOR_BGR2GRAY)

        small = cv2.resize(
            processed, (config.grid_w, config.grid_h), interpolation=cv2.INTER_AREA
        )
        chars = resolve_charset(config.charset)
        idx = (small / 255 * (len(chars) - 1)).astype(np.int32)

        out_w, out_h = self.output_size(config)
        img = Image.new("RGB", (out_w, out_h), color=(0, 0, 0))
        draw = ImageDraw.Draw(img)
        y = 0
        for row in idx:
            line = "".join(chars[i] for i in row)
            draw.text((0, y), line, fill=(255, 255, 255), font=self._font)
            y += self._char_h
        return img
