"""
app.py
------
Flask Web Dashboard for Real-Time Motion Detection System using OpenCV.
Features:
  - Video upload or built-in sample video selection
  - Adjustable detection parameters (algorithm, min-area, blur, threshold)
  - Live progress polling and telemetry
  - Side-by-side video playback (Input vs Motion Detected)
  - Interactive Chart.js analytics timeline
  - Snapshot gallery
  - Direct downloads for output video and CSV event report
"""

import os
import sys
import time
import threading
from typing import Dict, Any
import cv2
import numpy as np
from flask import (
    Flask,
    render_template,
    request,
    jsonify,
    send_from_directory,
    send_file,
    url_for,
)
from werkzeug.utils import secure_filename

from src.detector import MotionDetector
from src.visualizer import FrameVisualizer
from src.recorder import VideoRecorder, MotionLogger, SnapshotManager

import tempfile

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
IS_VERCEL = bool(os.environ.get("VERCEL"))
STORAGE_DIR = tempfile.gettempdir() if IS_VERCEL else BASE_DIR

UPLOAD_FOLDER = os.path.join(STORAGE_DIR, "uploads")
SNAPSHOT_FOLDER = os.path.join(STORAGE_DIR, "snapshots")
OUTPUT_FOLDER = os.path.join(STORAGE_DIR, "outputs")

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(SNAPSHOT_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

app = Flask(__name__)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = 500 * 1024 * 1024  # 500 MB max

ALLOWED_EXTENSIONS = {"mp4", "avi", "mov", "mkv", "webm"}

# Global thread-safe processing state
state_lock = threading.Lock()
processing_state: Dict[str, Any] = {
    "is_processing": False,
    "progress": 0,
    "frame_idx": 0,
    "total_frames": 0,
    "current_fps": 0.0,
    "status": "idle",  # 'idle', 'processing', 'completed', 'error'
    "error_message": "",
    "input_filename": "",
    "output_filename": "output_detected.mp4",
    "metrics": {
        "total_frames": 0,
        "duration_sec": 0.0,
        "processing_time_sec": 0.0,
        "avg_fps": 0.0,
        "total_events": 0,
        "peak_objects": 0,
        "max_motion_area": 0,
    },
    "chart_data": {
        "timestamps": [],
        "object_counts": [],
        "motion_areas": [],
    },
    "snapshots": [],
}


def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def background_processor(
    input_path: str,
    output_path: str,
    csv_path: str,
    min_area: int,
    method: str,
    blur_kernel: int = 21,
    threshold_val: int = 25,
    max_frames: int = None,
):
    global processing_state
    try:
        cap = cv2.VideoCapture(input_path)
        if not cap.isOpened():
            with state_lock:
                processing_state["is_processing"] = False
                processing_state["status"] = "error"
                processing_state["error_message"] = f"Unable to open video: {os.path.basename(input_path)}"
            return

        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)) or 1280
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)) or 720
        fps = cap.get(cv2.CAP_PROP_FPS)
        if fps <= 0 or fps is None or np.isnan(fps):
            fps = 30.0
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) or 1

        with state_lock:
            processing_state["total_frames"] = total_frames
            processing_state["progress"] = 0
            processing_state["status"] = "processing"
            processing_state["chart_data"] = {
                "timestamps": [],
                "object_counts": [],
                "motion_areas": [],
            }
            processing_state["snapshots"] = []

        # Initialize CV pipeline
        detector = MotionDetector(
            min_area=min_area,
            blur_size=(blur_kernel, blur_kernel),
            threshold_val=threshold_val,
            method=method,
        )
        visualizer = FrameVisualizer()
        recorder = VideoRecorder(output_path=output_path, fps=fps, frame_size=(width, height))
        logger = MotionLogger(csv_path=csv_path)
        snapshot_mgr = SnapshotManager(output_dir=SNAPSHOT_FOLDER, cooldown_sec=1.5)

        frame_idx = 0
        t_start = time.time()
        t_prev = t_start
        curr_fps = fps
        peak_objects_overall = 0
        max_area_overall = 0.0

        chart_sample_rate = max(1, int(fps / 5))  # Record ~5 data points per second for smooth chart
        collected_snapshots = []

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            frame_idx += 1
            if max_frames and frame_idx >= max_frames:
                break
            curr_time_sec = frame_idx / fps

            # 1. Motion Detection
            result = detector.process_frame(frame)

            obj_count = len(result.bounding_boxes)
            motion_area = result.total_motion_area
            peak_objects_overall = max(peak_objects_overall, obj_count)
            max_area_overall = max(max_area_overall, motion_area)

            # 2. Logger & Snapshot
            logger.update(
                has_motion=result.has_motion,
                time_sec=curr_time_sec,
                object_count=obj_count,
                motion_area=motion_area,
            )

            if result.has_motion:
                snap_path = snapshot_mgr.trigger(frame, curr_time_sec)
                if snap_path:
                    collected_snapshots.append(os.path.basename(snap_path))

            # 3. Annotate & Record
            t_now = time.time()
            if t_now - t_prev >= 0.2:
                curr_fps = 1.0 / max(1e-5, (t_now - t_prev))
                t_prev = t_now

            annotated = visualizer.annotate_frame(
                frame=frame,
                result=result,
                fps=curr_fps,
                frame_idx=frame_idx,
                time_sec=curr_time_sec,
            )
            recorder.write_frame(annotated)

            # 4. Periodic UI state update
            if frame_idx % chart_sample_rate == 0 or frame_idx == total_frames:
                with state_lock:
                    processing_state["chart_data"]["timestamps"].append(round(curr_time_sec, 2))
                    processing_state["chart_data"]["object_counts"].append(obj_count)
                    processing_state["chart_data"]["motion_areas"].append(int(motion_area))

            if frame_idx % 5 == 0 or frame_idx == total_frames:
                progress_pct = min(100, int((frame_idx / total_frames) * 100))
                with state_lock:
                    processing_state["frame_idx"] = frame_idx
                    processing_state["progress"] = progress_pct
                    processing_state["current_fps"] = round(curr_fps, 1)

        final_time_sec = frame_idx / fps
        logger.close(final_time_sec)
        recorder.release()
        cap.release()

        t_end = time.time()
        proc_time = t_end - t_start

        # Final state update
        with state_lock:
            processing_state["is_processing"] = False
            processing_state["progress"] = 100
            processing_state["status"] = "completed"
            processing_state["snapshots"] = collected_snapshots
            processing_state["metrics"] = {
                "total_frames": frame_idx,
                "duration_sec": round(final_time_sec, 2),
                "processing_time_sec": round(proc_time, 2),
                "avg_fps": round(frame_idx / max(1e-5, proc_time), 1),
                "total_events": logger.total_events,
                "peak_objects": peak_objects_overall,
                "max_motion_area": int(max_area_overall),
            }

    except Exception as e:
        with state_lock:
            processing_state["is_processing"] = False
            processing_state["status"] = "error"
            processing_state["error_message"] = str(e)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/upload", methods=["POST"])
def upload_video():
    if "video" not in request.files:
        return jsonify({"success": False, "error": "No file uploaded"}), 400

    file = request.files["video"]
    if file.filename == "":
        return jsonify({"success": False, "error": "Empty filename"}), 400

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        # Avoid collisions
        timestamp = int(time.time())
        save_name = f"{timestamp}_{filename}"
        filepath = os.path.join(app.config["UPLOAD_FOLDER"], save_name)
        file.save(filepath)

        return jsonify({
            "success": True,
            "filename": save_name,
            "original_name": filename,
            "url": f"/videos/uploads/{save_name}",
        })

    return jsonify({"success": False, "error": "Invalid file format. Supported: mp4, avi, mov, mkv, webm"}), 400


@app.route("/api/use_sample", methods=["POST"])
def use_sample_video():
    data = request.get_json(silent=True) or {}
    sample_type = data.get("type", "indoor")

    if sample_type == "traffic":
        filename = "demo_traffic.mp4"
        sample_file = os.path.join(BASE_DIR, filename)
        if not os.path.exists(sample_file):
            from generate_traffic_demo import generate_traffic_demo
            generate_traffic_demo(sample_file)
        name_label = "demo_traffic.mp4 (Street Intersection)"
    else:
        filename = "sample_input.mp4"
        sample_file = os.path.join(BASE_DIR, filename)
        if not os.path.exists(sample_file):
            from generate_sample_video import generate_sample_video
            generate_sample_video(sample_file)
        name_label = "sample_input.mp4 (Indoor Reception)"

    return jsonify({
        "success": True,
        "filename": filename,
        "label": name_label,
        "url": f"/videos/root/{filename}",
    })


@app.route("/api/process", methods=["POST"])
def start_processing():
    global processing_state
    with state_lock:
        if processing_state["is_processing"]:
            return jsonify({"success": False, "error": "Another video is currently being processed"}), 409

    data = request.get_json() or {}
    filename = data.get("filename", "")
    min_area = int(data.get("min_area", 1200))
    method = data.get("method", "accumulative")
    blur_kernel = int(data.get("blur_kernel", 21))
    threshold_val = int(data.get("threshold_val", 25))

    # Kernel must be odd
    if blur_kernel % 2 == 0:
        blur_kernel += 1

    # Determine input path
    if filename in ["sample_input.mp4", "demo_traffic.mp4"]:
        input_path = os.path.join(BASE_DIR, filename)
        input_stream_url = f"/videos/root/{filename}"
    else:
        input_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
        input_stream_url = f"/videos/uploads/{filename}"

    if not os.path.exists(input_path):
        return jsonify({"success": False, "error": f"Video file '{filename}' does not exist"}), 404

    output_filename = "output_detected.mp4"
    output_path = os.path.join(OUTPUT_FOLDER, output_filename)
    csv_path = os.path.join(OUTPUT_FOLDER, "motion_events.csv")

    with state_lock:
        processing_state["is_processing"] = True
        processing_state["progress"] = 0
        processing_state["status"] = "processing"
        processing_state["error_message"] = ""
        processing_state["input_filename"] = filename
        processing_state["output_filename"] = output_filename
        processing_state["input_video_url"] = input_stream_url
        processing_state["output_video_url"] = f"/videos/outputs/{output_filename}?t={int(time.time())}"
        processing_state["csv_url"] = f"/download/csv?t={int(time.time())}"

    if IS_VERCEL:
        # On Vercel serverless, run synchronously to avoid background thread suspension
        background_processor(
            input_path, output_path, csv_path, min_area, method, blur_kernel, threshold_val, max_frames=90
        )
        return jsonify({"success": True, "serverless": True, "message": "Motion detection completed on serverless"})

    # Launch background thread for local/dedicated server
    t = threading.Thread(
        target=background_processor,
        args=(input_path, output_path, csv_path, min_area, method, blur_kernel, threshold_val),
        daemon=True,
    )
    t.start()

    return jsonify({"success": True, "serverless": False, "message": "Motion detection started"})


@app.route("/api/progress")
def get_progress():
    with state_lock:
        return jsonify({
            "is_processing": processing_state["is_processing"],
            "progress": processing_state["progress"],
            "frame_idx": processing_state["frame_idx"],
            "total_frames": processing_state["total_frames"],
            "current_fps": processing_state["current_fps"],
            "status": processing_state["status"],
            "error_message": processing_state["error_message"],
        })


@app.route("/api/results")
def get_results():
    with state_lock:
        return jsonify({
            "status": processing_state["status"],
            "metrics": processing_state["metrics"],
            "chart_data": processing_state["chart_data"],
            "snapshots": [f"/snapshots/{s}" for s in processing_state["snapshots"]],
            "input_video_url": processing_state["input_video_url"],
            "output_video_url": processing_state["output_video_url"],
            "csv_url": processing_state["csv_url"],
        })


@app.route("/videos/<path:subpath>")
def serve_video(subpath):
    parts = subpath.split("/", 1)
    if len(parts) == 2:
        folder_type, fname = parts
        if folder_type == "uploads":
            return send_from_directory(UPLOAD_FOLDER, fname)
        elif folder_type == "outputs":
            return send_from_directory(OUTPUT_FOLDER, fname)
        elif folder_type == "root":
            return send_from_directory(BASE_DIR, fname)
    return send_from_directory(BASE_DIR, subpath)


@app.route("/snapshots/<filename>")
def serve_snapshot(filename):
    return send_from_directory(SNAPSHOT_FOLDER, filename)


@app.route("/download/<file_type>")
def download_file(file_type):
    if file_type == "video":
        filepath = os.path.join(OUTPUT_FOLDER, "output_detected.mp4")
        if os.path.exists(filepath):
            return send_file(filepath, as_attachment=True, download_name="motion_detected_output.mp4")
    elif file_type == "csv":
        filepath = os.path.join(OUTPUT_FOLDER, "motion_events.csv")
        if os.path.exists(filepath):
            return send_file(filepath, as_attachment=True, download_name="motion_events.csv")

    return jsonify({"error": "File not found"}), 404


if __name__ == "__main__":
    print("\n" + "=" * 65)
    print("  REAL-TIME MOTION DETECTION SYSTEM - WEB DASHBOARD")
    print("=" * 65)
    print("  Dashboard URL : http://127.0.0.1:5000")
    print("  Press Ctrl+C to stop the server.")
    print("=" * 65 + "\n")
    app.run(host="127.0.0.1", port=5000, debug=False, threaded=True)
