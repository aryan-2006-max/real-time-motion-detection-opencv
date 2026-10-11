"""
src/recorder.py
---------------
Media and event export modules:
  1. VideoRecorder: Encodes and saves annotated output video frames.
  2. MotionLogger: Records motion incidents and duration intervals to CSV.
  3. SnapshotManager: Saves high-resolution snapshot images upon motion detection.
"""

import os
import csv
import time
from typing import Tuple, Optional
import cv2
import numpy as np


class VideoRecorder:
    """
    Encapsulates cv2.VideoWriter with automatic codec resolution and directory creation.
    """

    def __init__(self, output_path: str, fps: float, frame_size: Tuple[int, int]):
        self.output_path = output_path
        self.fps = fps
        self.frame_size = frame_size  # (width, height)
        self.writer: Optional[cv2.VideoWriter] = None

        os.makedirs(os.path.dirname(os.path.abspath(output_path)) or ".", exist_ok=True)
        self._init_writer()

    def _init_writer(self):
        # Try mp4v first, then XVID
        if self.output_path.lower().endswith(".avi"):
            fourcc = cv2.VideoWriter_fourcc(*'XVID')
        else:
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')

        self.writer = cv2.VideoWriter(self.output_path, fourcc, self.fps, self.frame_size)

        if not self.writer.isOpened() and not self.output_path.lower().endswith(".avi"):
            # Fallback to AVI if MP4 container isn't supported by local backend
            fallback_path = os.path.splitext(self.output_path)[0] + ".avi"
            print(f"[RECORDER] mp4v codec failed. Falling back to: {fallback_path}")
            self.output_path = fallback_path
            fourcc = cv2.VideoWriter_fourcc(*'XVID')
            self.writer = cv2.VideoWriter(self.output_path, fourcc, self.fps, self.frame_size)

    def write_frame(self, frame: np.ndarray):
        """Write a single frame to the video output file."""
        if self.writer and self.writer.isOpened():
            # Ensure frame matches target dimensions
            if (frame.shape[1], frame.shape[0]) != self.frame_size:
                frame = cv2.resize(frame, self.frame_size)
            self.writer.write(frame)

    def release(self):
        """Finalize and close the video writer."""
        if self.writer:
            self.writer.release()
            self.writer = None


class MotionLogger:
    """
    Tracks and exports motion activity logs and continuous event durations to CSV.
    """

    def __init__(self, csv_path: str = "motion_events.csv"):
        self.csv_path = csv_path
        os.makedirs(os.path.dirname(os.path.abspath(csv_path)) or ".", exist_ok=True)

        self._in_motion_event = False
        self._event_id = 0
        self._event_start_time = 0.0
        self._peak_objects = 0
        self._max_motion_area = 0.0
        self.total_events = 0

        # Initialize CSV header
        with open(self.csv_path, mode="w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                "Event_ID",
                "Start_Time_Sec",
                "End_Time_Sec",
                "Duration_Sec",
                "Peak_Object_Count",
                "Max_Motion_Area_Px",
            ])

    def update(self, has_motion: bool, time_sec: float, object_count: int, motion_area: float):
        """Update tracker with frame state and flush completed events to CSV."""
        if has_motion and not self._in_motion_event:
            # Motion event started
            self._in_motion_event = True
            self._event_id += 1
            self._event_start_time = time_sec
            self._peak_objects = object_count
            self._max_motion_area = motion_area
        elif has_motion and self._in_motion_event:
            # Motion continues
            self._peak_objects = max(self._peak_objects, object_count)
            self._max_motion_area = max(self._max_motion_area, motion_area)
        elif not has_motion and self._in_motion_event:
            # Motion ended
            self._record_event(time_sec)
            self._in_motion_event = False

    def _record_event(self, end_time_sec: float):
        duration = max(0.0, end_time_sec - self._event_start_time)
        with open(self.csv_path, mode="a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                self._event_id,
                f"{self._event_start_time:.2f}",
                f"{end_time_sec:.2f}",
                f"{duration:.2f}",
                self._peak_objects,
                int(self._max_motion_area),
            ])
        self.total_events += 1

    def close(self, final_time_sec: float = 0.0):
        """Flush any currently ongoing motion event at video end."""
        if self._in_motion_event:
            self._record_event(final_time_sec)
            self._in_motion_event = False


class SnapshotManager:
    """
    Saves snapshot images when motion is detected, using a cooldown to avoid flooding.
    """

    def __init__(self, output_dir: str = "snapshots", cooldown_sec: float = 1.5):
        self.output_dir = output_dir
        self.cooldown_sec = cooldown_sec
        self.last_saved_time = -999.0
        self.snapshot_count = 0
        os.makedirs(self.output_dir, exist_ok=True)

    def trigger(self, frame: np.ndarray, time_sec: float) -> Optional[str]:
        """Save a snapshot if motion is active and cooldown has passed."""
        if time_sec - self.last_saved_time >= self.cooldown_sec:
            self.last_saved_time = time_sec
            self.snapshot_count += 1
            filename = f"motion_event_{self.snapshot_count:03d}_{time_sec:.1f}s.jpg"
            filepath = os.path.join(self.output_dir, filename)
            cv2.imwrite(filepath, frame)
            return filepath
        return None
