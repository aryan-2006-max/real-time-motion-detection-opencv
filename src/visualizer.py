"""
src/visualizer.py
-----------------
Visual HUD (Heads-Up Display) and Multi-View Dashboard for OpenCV Motion Detection.
Provides bounding box rendering, status overlays, metrics badges, and 2x2 grid views.
"""

from typing import Tuple, Optional
import cv2
import numpy as np
from src.detector import DetectionResult


class FrameVisualizer:
    """
    Renders visual annotations, HUD indicators, and multi-view grids onto video frames.
    """

    def __init__(self, box_color: Tuple[int, int, int] = (0, 0, 255), box_thickness: int = 2):
        self.box_color = box_color  # Red bounding boxes
        self.box_thickness = box_thickness

    def annotate_frame(
        self,
        frame: np.ndarray,
        result: DetectionResult,
        fps: float = 0.0,
        frame_idx: int = 0,
        time_sec: float = 0.0,
    ) -> np.ndarray:
        """
        Draw bounding boxes, centroids, and HUD status header onto the frame.

        Args:
            frame: Raw BGR input frame.
            result: DetectionResult from MotionDetector.
            fps: Current processing frame rate.
            frame_idx: Current frame index.
            time_sec: Video timestamp in seconds.

        Returns:
            Annotated BGR frame copy.
        """
        annotated = frame.copy()
        height, width = annotated.shape[:2]

        # 1. Draw bounding boxes & centroids for moving objects
        for idx, (x, y, w, h) in enumerate(result.bounding_boxes, start=1):
            # Dynamic color: Red for active motion boxes
            cv2.rectangle(annotated, (x, y), (x + w, y + h), (0, 0, 255), self.box_thickness)

            # Centroid point
            if idx - 1 < len(result.centroids):
                cx, cy = result.centroids[idx - 1]
                cv2.circle(annotated, (cx, cy), 5, (0, 255, 255), -1)

            # Object label tag with area
            area = result.contour_areas[idx - 1] if idx - 1 < len(result.contour_areas) else 0
            label = f"Target #{idx} ({int(area)}px)"
            (lw, lh), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.45, 1)

            # Tag background
            tag_y1 = max(0, y - lh - 8)
            cv2.rectangle(annotated, (x, tag_y1), (x + lw + 6, y), (0, 0, 180), -1)
            cv2.putText(
                annotated,
                label,
                (x + 3, y - 4),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.45,
                (255, 255, 255),
                1,
                cv2.LINE_AA,
            )

        # 2. Modern Translucent HUD Bar at the Top
        hud_bar_height = 52
        overlay = annotated.copy()
        cv2.rectangle(overlay, (0, 0), (width, hud_bar_height), (20, 20, 20), -1)
        cv2.addWeighted(overlay, 0.75, annotated, 0.25, 0, annotated)

        # Bottom border for HUD bar
        cv2.line(annotated, (0, hud_bar_height), (width, hud_bar_height), (70, 70, 70), 1)

        # 3. Status Badge: MOTION DETECTED (Red) vs NO MOTION (Green)
        if result.has_motion:
            badge_text = f"● MOTION DETECTED [{len(result.bounding_boxes)} OBJECT(S)]"
            badge_color = (0, 0, 255)  # Bright Red
        else:
            badge_text = "● SYSTEM ACTIVE: NO MOTION"
            badge_color = (0, 220, 80)  # Bright Green

        cv2.putText(
            annotated,
            badge_text,
            (18, 33),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.65,
            badge_color,
            2,
            cv2.LINE_AA,
        )

        # 4. Right-side Metrics: FPS & Timecode
        mins = int(time_sec // 60)
        secs = int(time_sec % 60)
        millis = int((time_sec % 1) * 100)
        timecode = f"Time: {mins:02d}:{secs:02d}.{millis:02d} | Frame: {frame_idx}"
        fps_text = f"FPS: {fps:.1f}"

        stats_str = f"{fps_text}  |  {timecode}"
        (sw, _), _ = cv2.getTextSize(stats_str, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
        cv2.putText(
            annotated,
            stats_str,
            (width - sw - 18, 33),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (210, 210, 210),
            1,
            cv2.LINE_AA,
        )

        return annotated

    def create_multiview_dashboard(
        self,
        raw_frame: np.ndarray,
        gray_frame: Optional[np.ndarray],
        thresh_mask: Optional[np.ndarray],
        annotated_frame: np.ndarray,
        target_size: Tuple[int, int] = (1280, 720),
    ) -> np.ndarray:
        """
        Combine 4 views into a 2x2 comparison dashboard:
          [ Top-Left: Original Input ]         [ Top-Right: Grayscale Blur ]
          [ Bottom-Left: Threshold Mask ]      [ Bottom-Right: Motion Detection (Final) ]
        """
        grid_w, grid_h = target_size[0] // 2, target_size[1] // 2

        # 1. Raw Frame
        v1 = cv2.resize(raw_frame, (grid_w, grid_h))
        self._add_panel_label(v1, "1. RAW INPUT VIDEO")

        # 2. Gray Blurred
        if gray_frame is not None:
            gray_bgr = cv2.cvtColor(gray_frame, cv2.COLOR_GRAY2BGR)
            v2 = cv2.resize(gray_bgr, (grid_w, grid_h))
        else:
            v2 = np.zeros((grid_h, grid_w, 3), dtype=np.uint8)
        self._add_panel_label(v2, "2. GAUSSIAN BLUR (GRAY)")

        # 3. Binary Threshold Mask
        if thresh_mask is not None:
            mask_bgr = cv2.cvtColor(thresh_mask, cv2.COLOR_GRAY2BGR)
            # Tint motion white regions with bright cyan for visibility
            mask_bgr[thresh_mask > 0] = [255, 200, 50]
            v3 = cv2.resize(mask_bgr, (grid_w, grid_h))
        else:
            v3 = np.zeros((grid_h, grid_w, 3), dtype=np.uint8)
        self._add_panel_label(v3, "3. MOTION THRESHOLD MASK")

        # 4. Annotated Output Frame
        v4 = cv2.resize(annotated_frame, (grid_w, grid_h))
        self._add_panel_label(v4, "4. FINAL MOTION DETECTION")

        # Combine into 2x2 grid
        top_row = np.hstack([v1, v2])
        bottom_row = np.hstack([v3, v4])
        dashboard = np.vstack([top_row, bottom_row])

        # Grid separator lines
        cv2.line(dashboard, (grid_w, 0), (grid_w, target_size[1]), (60, 60, 60), 2)
        cv2.line(dashboard, (0, grid_h), (target_size[0], grid_h), (60, 60, 60), 2)

        return dashboard

    @staticmethod
    def _add_panel_label(panel: np.ndarray, label: str):
        """Helper to render a subtle dark badge with white text in the panel header."""
        cv2.rectangle(panel, (8, 8), (240, 32), (30, 30, 30), -1)
        cv2.rectangle(panel, (8, 8), (240, 32), (80, 80, 80), 1)
        cv2.putText(
            panel,
            label,
            (14, 25),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.45,
            (255, 255, 255),
            1,
            cv2.LINE_AA,
        )
