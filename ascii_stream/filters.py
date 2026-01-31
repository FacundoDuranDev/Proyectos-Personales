from typing import Protocol

import cv2
import numpy as np

from .config import AsciiStreamConfig


class FrameFilter(Protocol):
    def apply(self, frame: np.ndarray, config: AsciiStreamConfig) -> np.ndarray:
        ...


class GrayscaleFilter:
    def apply(self, frame: np.ndarray, config: AsciiStreamConfig) -> np.ndarray:
        if frame.ndim == 2:
            return frame
        return cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)


class ContrastBrightnessFilter:
    def apply(self, frame: np.ndarray, config: AsciiStreamConfig) -> np.ndarray:
        if config.contrast == 1.0 and config.brightness == 0:
            return frame
        return cv2.convertScaleAbs(
            frame, alpha=float(config.contrast), beta=int(config.brightness)
        )


class InvertFilter:
    def apply(self, frame: np.ndarray, config: AsciiStreamConfig) -> np.ndarray:
        if not config.invert:
            return frame
        return 255 - frame
