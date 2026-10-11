"""
src/detector.py
---------------
Core Computer Vision Motion Detector using OpenCV.
Supports:
  1. Accumulative Running Average Background Differencing (robust to subtle lighting shifts)
  2. Gaussian Mixture-based Background/Foreground Subtraction (MOG2)
"""

from dataclasses import dataclass, field
from typing import List, Tuple, Optional
import cv2
import numpy as np


@dataclass
class DetectionResult:
    """Encapsulates the motion detection output for a single video frame."""
    has_motion: bool
    bounding_boxes: List[Tuple[int, int, int, int]] = field(default_factory=list)
    centroids: List[Tuple[int, int]] = field(default_factory=list)
    contour_areas: List[float] = field(default_factory=list)
    total_motion_area: float = 0.0
    gray_frame: Optional[np.ndarray] = None
    delta_frame: Optional[np.ndarray] = None
    threshold_mask: Optional[np.ndarray] = None


class MotionDetector:
    """
    Real-time Motion Detection Engine.
    
    Attributes:
        min_area (int): Minimum contour area in pixels to be recognized as motion.
        blur_size (Tuple[int, int]): Kernel size for Gaussian blurring (noise suppression).
        threshold_val (int): Pixel intensity threshold for frame differencing.
        accum_weight (float): Learning rate for running average background update (0.0 to 1.0).
        method (str): 'accumulative' or 'mog2'.
    """

    def __init__(
        self,
        min_area: int = 1200,
        blur_size: Tuple[int, int] = (21, 21),
        threshold_val: int = 25,
        accum_weight: float = 0.05,
        method: str = "accumulative",
    ):
        self.min_area = min_area
        self.blur_size = blur_size
        self.threshold_val = threshold_val
        self.accum_weight = accum_weight
        self.method = method.lower()

        # Background state
        self._background_model: Optional[np.ndarray] = None

        # MOG2 Subtractor instance if requested
        if self.method == "mog2":
            self._subtractor = cv2.createBackgroundSubtractorMOG2(
                history=500, varThreshold=16, detectShadows=True
            )
        else:
            self._subtractor = None

    def reset(self):
        """Reset the internal background model (e.g., when switching video feeds)."""
        self._background_model = None
        if self._subtractor is not None:
            self._subtractor = cv2.createBackgroundSubtractorMOG2(
                history=500, varThreshold=16, detectShadows=True
            )

    def process_frame(self, frame: np.ndarray) -> DetectionResult:
        """
        Process a single BGR video frame and compute motion contours.

        Args:
            frame: Input BGR image from OpenCV VideoCapture.

        Returns:
            DetectionResult containing detected bounding boxes, masks, and motion flag.
        """
        if frame is None:
            return DetectionResult(has_motion=False)

        # 1. Grayscale conversion: simplifies 3-channel BGR to luminance
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        # 2. Gaussian Blur: smoothens high-frequency sensor noise and camera jitter
        gray_blur = cv2.GaussianBlur(gray, self.blur_size, 0)

        # 3. Background modeling & differencing
        if self.method == "mog2":
            # MOG2 foreground mask (0: bg, 127: shadow, 255: fg)
            fg_mask = self._subtractor.apply(gray_blur)
            # Remove shadows by thresholding out pixel values below 200
            _, thresh = cv2.threshold(fg_mask, 200, 255, cv2.THRESH_BINARY)
            delta_frame = fg_mask
        else:
            # Accumulative weighted average background modeling
            if self._background_model is None:
                self._background_model = gray_blur.astype("float")
                return DetectionResult(
                    has_motion=False,
                    gray_frame=gray_blur,
                    delta_frame=np.zeros_like(gray_blur),
                    threshold_mask=np.zeros_like(gray_blur),
                )

            # Update running average background model:
            # bg = (1 - alpha) * bg + alpha * current_frame
            cv2.accumulateWeighted(gray_blur, self._background_model, self.accum_weight)

            # Compute absolute difference between background model and current frame
            delta_frame = cv2.absdiff(gray_blur, cv2.convertScaleAbs(self._background_model))

            # Apply binary thresholding: pixels with diff > threshold become 255 (white)
            _, thresh = cv2.threshold(delta_frame, self.threshold_val, 255, cv2.THRESH_BINARY)

        # 4. Morphological Dilation: fills in small holes/gaps inside detected regions
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
        thresh_dilated = cv2.dilate(thresh, kernel, iterations=2)

        # 5. Contour Detection: locate boundaries of moving regions
        contours, _ = cv2.findContours(
            thresh_dilated.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )

        bounding_boxes = []
        centroids = []
        contour_areas = []
        total_motion_area = 0.0

        for c in contours:
            area = cv2.contourArea(c)
            # Filter out small contours below threshold (insects, leaf flickers, noise)
            if area < self.min_area:
                continue

            # Compute bounding box
            (x, y, w, h) = cv2.boundingRect(c)
            bounding_boxes.append((x, y, w, h))
            contour_areas.append(area)
            total_motion_area += area

            # Calculate centroid using image moments
            M = cv2.moments(c)
            if M["m00"] != 0:
                cx = int(M["m10"] / M["m00"])
                cy = int(M["m01"] / M["m00"])
            else:
                cx, cy = x + w // 2, y + h // 2
            centroids.append((cx, cy))

        has_motion = len(bounding_boxes) > 0

        return DetectionResult(
            has_motion=has_motion,
            bounding_boxes=bounding_boxes,
            centroids=centroids,
            contour_areas=contour_areas,
            total_motion_area=total_motion_area,
            gray_frame=gray_blur,
            delta_frame=delta_frame,
            threshold_mask=thresh_dilated,
        )
