"""
main.py
-------
Entry point for the Real-Time Motion Detection System using OpenCV.

Usage:
  1. Interactive mode:
       python main.py
  2. Command line mode:
       python main.py --input sample_input.mp4 --output output_detected.mp4
  3. Webcam live mode:
       python main.py --input 0
  4. Headless processing (no GUI display):
       python main.py --input sample_input.mp4 --no-display
"""

import os
import sys
import time
import math
import argparse
import cv2
import numpy as np

from src.detector import MotionDetector
from src.visualizer import FrameVisualizer
from src.recorder import VideoRecorder, MotionLogger, SnapshotManager


BANNER = r"""
======================================================================
     REAL-TIME MOTION DETECTION SYSTEM USING OPENCV
======================================================================
 Algorithms: Accumulative Weighted Background Modeling / MOG2
 Controls during playback:
   [q] : Quit and finalize output video
   [p] : Pause / Resume video
   [m] : Toggle Multi-View Dashboard (Original, Blur, Mask, Output)
   [s] : Save instant snapshot to snapshots/
======================================================================
"""


def parse_args():
    parser = argparse.ArgumentParser(
        description="Real-Time Motion Detection System using OpenCV"
    )
    parser.add_argument(
        "-i", "--input",
        type=str,
        default=None,
        help="Path to input video file (e.g., 'sample.mp4') or camera index ('0' for webcam)",
    )
    parser.add_argument(
        "-o", "--output",
        type=str,
        default="output_detected.mp4",
        help="Path to save the motion-detected output video (default: output_detected.mp4)",
    )
    parser.add_argument(
        "-a", "--min-area",
        type=int,
        default=1200,
        help="Minimum contour area in pixels to trigger motion detection (default: 1200)",
    )
    parser.add_argument(
        "-m", "--method",
        type=str,
        default="accumulative",
        choices=["accumulative", "mog2"],
        help="Motion detection algorithm: 'accumulative' or 'mog2' (default: accumulative)",
    )
    parser.add_argument(
        "--multi-view",
        action="store_true",
        help="Launch directly in 2x2 multi-view comparison mode",
    )
    parser.add_argument(
        "--no-display",
        action="store_true",
        help="Headless processing mode: process video and save output without opening a GUI window",
    )
    parser.add_argument(
        "--log",
        type=str,
        default="motion_events.csv",
        help="Path to save CSV motion event timeline (default: motion_events.csv)",
    )
    parser.add_argument(
        "--snapshots",
        action="store_true",
        default=True,
        help="Automatically capture snapshots when motion is detected (default: True)",
    )
    return parser.parse_args()


def interactive_select_source() -> str:
    """Prompt user to select video source if not provided via command line."""
    print(BANNER)
    print("Please select an input video source:")
    print("  [1] Use synthetic demo video ('sample_input.mp4')")
    print("  [2] Enter path to your video file")
    print("  [3] Use live webcam (Device 0)")
    print()

    choice = input("Enter choice [1/2/3] (default: 1): ").strip()
    if choice == "2":
        path = input("Enter video file path: ").strip().strip('"').strip("'")
        while not os.path.exists(path):
            print(f"Error: File '{path}' not found!")
            path = input("Enter valid video file path (or 'q' to cancel): ").strip().strip('"').strip("'")
            if path.lower() == 'q':
                sys.exit(0)
        return path
    elif choice == "3":
        return "0"
    else:
        sample_path = "sample_input.mp4"
        if not os.path.exists(sample_path):
            print("\nDemo video not found. Generating synthetic test video now...")
            from generate_sample_video import generate_sample_video
            generated = generate_sample_video(sample_path)
            if generated:
                sample_path = generated
        return sample_path


def run_motion_detection(
    input_source: str,
    output_path: str = "output_detected.mp4",
    min_area: int = 1200,
    method: str = "accumulative",
    multi_view: bool = False,
    no_display: bool = False,
    csv_log_path: str = "motion_events.csv",
    save_snapshots: bool = True,
):
    print(f"\n[INIT] Initializing Motion Detection Pipeline...")
    print(f"  Input Source    : {input_source}")
    print(f"  Output Video    : {output_path}")
    print(f"  Algorithm       : {method.upper()}")
    print(f"  Min Contour Area: {min_area} px")
    print(f"  Display Mode    : {'Headless (No GUI)' if no_display else ('Multi-View 2x2' if multi_view else 'Annotated Single-View')}")

    # Determine if input is webcam or file
    if input_source.isdigit():
        cap = cv2.VideoCapture(int(input_source))
        is_live_stream = True
    else:
        if not os.path.exists(input_source):
            print(f"[ERROR] Input video '{input_source}' does not exist.")
            sys.exit(1)
        cap = cv2.VideoCapture(input_source)
        is_live_stream = False

    if not cap.isOpened():
        print(f"[ERROR] Could not open video source '{input_source}'.")
        sys.exit(1)

    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)) or 1280
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)) or 720
    fps = cap.get(cv2.CAP_PROP_FPS)
    if fps <= 0 or fps is None or np.isnan(fps):
        fps = 30.0
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) if not is_live_stream else 0

    print(f"  Resolution      : {width}x{height}")
    print(f"  Source FPS      : {fps:.2f}")
    if total_frames > 0:
        print(f"  Total Frames    : {total_frames} (~{total_frames / fps:.1f}s)")

    # Initialize modules
    detector = MotionDetector(min_area=min_area, method=method)
    visualizer = FrameVisualizer()
    recorder = VideoRecorder(output_path=output_path, fps=fps, frame_size=(width, height))
    logger = MotionLogger(csv_path=csv_log_path)
    snapshot_mgr = SnapshotManager() if save_snapshots else None

    window_name = "Real-Time Motion Detection System - OpenCV"
    if not no_display:
        cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
        cv2.resizeWindow(window_name, min(1280, width), min(720, height))

    frame_idx = 0
    t_start = time.time()
    t_prev = t_start
    curr_fps = fps
    is_paused = False

    print("\n[RUNNING] Processing started. Press 'q' in video window to exit.")

    try:
        while True:
            if not is_paused:
                ret, frame = cap.read()
                if not ret:
                    break

                frame_idx += 1
                curr_time_sec = frame_idx / fps if not is_live_stream else (time.time() - t_start)

                # 1. Computer Vision Motion Detection
                result = detector.process_frame(frame)

                # 2. Update Event Logger & Snapshots
                logger.update(
                    has_motion=result.has_motion,
                    time_sec=curr_time_sec,
                    object_count=len(result.bounding_boxes),
                    motion_area=result.total_motion_area,
                )

                if result.has_motion and snapshot_mgr:
                    snapshot_path = snapshot_mgr.trigger(frame, curr_time_sec)
                    if snapshot_path:
                        print(f"  [SNAPSHOT] Motion triggered at {curr_time_sec:.1f}s -> Saved: {snapshot_path}")

                # 3. Calculate FPS
                t_now = time.time()
                dt = t_now - t_prev
                if dt >= 0.2:
                    curr_fps = 1.0 / max(1e-5, (t_now - t_prev))
                    t_prev = t_now

                # 4. Annotate Frame
                annotated_frame = visualizer.annotate_frame(
                    frame=frame,
                    result=result,
                    fps=curr_fps,
                    frame_idx=frame_idx,
                    time_sec=curr_time_sec,
                )

                # 5. Output Video Recording
                recorder.write_frame(annotated_frame)

                # 6. Display or Console progress
                if not no_display:
                    if multi_view:
                        display_frame = visualizer.create_multiview_dashboard(
                            raw_frame=frame,
                            gray_frame=result.gray_frame,
                            thresh_mask=result.threshold_mask,
                            annotated_frame=annotated_frame,
                            target_size=(width, height),
                        )
                    else:
                        display_frame = annotated_frame

                    cv2.imshow(window_name, display_frame)
                else:
                    if frame_idx % 30 == 0 or frame_idx == total_frames:
                        pct = f"({(frame_idx / total_frames * 100):.1f}%)" if total_frames > 0 else ""
                        status_str = f"MOTION [{len(result.bounding_boxes)}]" if result.has_motion else "IDLE"
                        print(f"  Frame {frame_idx:04d} {pct} | Status: {status_str} | FPS: {curr_fps:.1f}")

            # Handle Keyboard Input
            if not no_display:
                # Wait 1ms (or appropriate delay to mimic original framerate)
                delay_ms = max(1, int(1000 / fps)) if not is_live_stream else 1
                key = cv2.waitKey(delay_ms if not is_paused else 50) & 0xFF

                if key == ord('q'):
                    print("[USER] Quitting session...")
                    break
                elif key == ord('p'):
                    is_paused = not is_paused
                    print(f"[USER] {'PAUSED' if is_paused else 'RESUMED'}")
                elif key == ord('m'):
                    multi_view = not multi_view
                    print(f"[USER] Multi-View toggled: {'ON (2x2 Grid)' if multi_view else 'OFF (Single View)'}")
                elif key == ord('s'):
                    if snapshot_mgr:
                        manual_snap = os.path.join(snapshot_mgr.output_dir, f"manual_{int(time.time())}.jpg")
                        cv2.imwrite(manual_snap, annotated_frame)
                        print(f"[USER] Manual snapshot saved: {manual_snap}")

    except KeyboardInterrupt:
        print("\n[INTERRUPT] Interrupted by user.")
    finally:
        # Cleanup & summary
        final_time = frame_idx / fps if not is_live_stream else (time.time() - t_start)
        logger.close(final_time)
        recorder.release()
        cap.release()
        if not no_display:
            cv2.destroyAllWindows()

    total_proc_time = time.time() - t_start
    print("\n" + "=" * 60)
    print("             MOTION DETECTION SUMMARY REPORT")
    print("=" * 60)
    print(f" Total Frames Processed : {frame_idx}")
    print(f" Total Video Duration   : {final_time:.2f} seconds")
    print(f" Total Processing Time  : {total_proc_time:.2f} seconds")
    print(f" Average Processing FPS : {frame_idx / max(1e-5, total_proc_time):.1f} FPS")
    print(f" Total Motion Incidents : {logger.total_events} event(s)")
    print(f" Output Video Generated : {recorder.output_path}")
    print(f" Motion Events Log      : {csv_log_path}")
    if snapshot_mgr and snapshot_mgr.snapshot_count > 0:
        print(f" Snapshots Saved        : {snapshot_mgr.snapshot_count} in '{snapshot_mgr.output_dir}/'")
    print("=" * 60 + "\n")


def main():
    args = parse_args()
    input_source = args.input

    if input_source is None:
        input_source = interactive_select_source()

    run_motion_detection(
        input_source=input_source,
        output_path=args.output,
        min_area=args.min_area,
        method=args.method,
        multi_view=args.multi_view,
        no_display=args.no_display,
        csv_log_path=args.log,
        save_snapshots=args.snapshots,
    )


if __name__ == "__main__":
    main()
