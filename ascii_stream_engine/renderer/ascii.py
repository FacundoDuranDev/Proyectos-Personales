from typing import List, Optional, Tuple

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from ..core.config import EngineConfig
from ..core.types import RenderFrame


class AsciiRenderer:
    def __init__(self, font: Optional[ImageFont.ImageFont] = None) -> None:
        self._font = font or ImageFont.load_default()
        bbox = self._font.getbbox("A")
        self._char_w = bbox[2] - bbox[0]
        self._char_h = bbox[3] - bbox[1]

    def output_size(self, config: EngineConfig) -> Tuple[int, int]:
        return config.grid_w * self._char_w, config.grid_h * self._char_h

    def _frame_to_lines(self, frame: np.ndarray, config: EngineConfig) -> List[str]:
        if frame.ndim == 3:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        else:
            gray = frame
        small = cv2.resize(
            gray, (config.grid_w, config.grid_h), interpolation=cv2.INTER_AREA
        )
        chars = config.charset
        idx = (small / 255 * (len(chars) - 1)).astype(np.int32)
        return ["".join(chars[i] for i in row) for row in idx]

    def render(
        self, frame: np.ndarray, config: EngineConfig, analysis: Optional[dict] = None
    ) -> RenderFrame:
        lines = self._frame_to_lines(frame, config)
        text = "\n".join(lines)
        out_w, out_h = self.output_size(config)
        img = Image.new("RGB", (out_w, out_h), color=(0, 0, 0))
        draw = ImageDraw.Draw(img)
        y = 0
        for line in lines:
            draw.text((0, y), line, fill=(255, 255, 255), font=self._font)
            y += self._char_h
        metadata = {"analysis": analysis or {}}
        return RenderFrame(image=img, text=text, lines=lines, metadata=metadata)
