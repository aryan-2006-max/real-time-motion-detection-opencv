"""
generate_sample_video.py
------------------------
Utility script to generate a synthetic test video for motion detection.
Creates a 10-second video (1280x720 at 30 FPS) with:
  1. Static room/scene background (0 - 1.5s)
  2. A moving rectangle ("agent / person") moving across the room (1.5s - 6s)
  3. A second moving circular object entering and moving downwards (4s - 8s)
  4. Final static period (8s - 10s)
"""

import sys
import numpy as np

def generate_sample_video(output_path="sample_input.mp4", duration_sec=10, fps=30, width=1280, height=720):
    try:
        import cv2
    except ImportError:
        print("OpenCV is not installed yet. Please run: pip install opencv-python")
        sys.exit(1)

    total_frames = duration_sec * fps
    print(f"Generating synthetic sample video: '{output_path}'")
    print(f"Resolution: {width}x{height} | FPS: {fps} | Total Frames: {total_frames}")

    # Use mp4v codec
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

    if not out.isOpened():
        print("Warning: mp4v codec failed, trying XVID with .avi fallback...")
        output_path = output_path.replace(".mp4", ".avi")
        fourcc = cv2.VideoWriter_fourcc(*'XVID')
        out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

    if not out.isOpened():
        print("Error: Could not open VideoWriter. Check OpenCV codecs.")
        return None

    # Base background: simulated indoor surveillance view
    base_bg = np.zeros((height, width, 3), dtype=np.uint8)
    # Wall gradient (top half)
    for y in range(int(height * 0.65)):
        val = int(180 - (y / (height * 0.65)) * 40)
        base_bg[y, :] = (val, val + 10, val + 20)  # Soft warm beige wall

    # Floor (bottom half)
    for y in range(int(height * 0.65), height):
        ratio = (y - height * 0.65) / (height * 0.35)
        val = int(80 + ratio * 30)
        base_bg[y, :] = (val, val, val + 15)  # Wooden / gray floor tiles

    # Static features: Doorway
    cv2.rectangle(base_bg, (100, 150), (280, int(height * 0.65)), (100, 70, 50), -1)
    cv2.rectangle(base_bg, (100, 150), (280, int(height * 0.65)), (60, 40, 30), 4)
    cv2.circle(base_bg, (260, int(height * 0.42)), 6, (220, 200, 100), -1)

    # Static features: Table / desk
    cv2.rectangle(base_bg, (850, 420), (1200, 560), (90, 80, 70), -1)
    cv2.rectangle(base_bg, (850, 420), (1200, 560), (50, 45, 40), 3)
    # Desk legs
    cv2.rectangle(base_bg, (870, 560), (900, 680), (60, 55, 50), -1)
    cv2.rectangle(base_bg, (1150, 560), (1180, 680), (60, 55, 50), -1)

    # Static features: Wall clock
    cv2.circle(base_bg, (640, 120), 45, (240, 240, 240), -1)
    cv2.circle(base_bg, (640, 120), 45, (40, 40, 40), 3)
    cv2.line(base_bg, (640, 120), (640, 95), (20, 20, 20), 3)
    cv2.line(base_bg, (640, 120), (665, 120), (20, 20, 20), 3)

    # Camera label header
    cv2.putText(base_bg, "CAM-01 [INDOOR RECEPTION]", (30, 40),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (240, 240, 240), 2, cv2.LINE_AA)

    print("Rendering frames...")
    for frame_idx in range(total_frames):
        frame = base_bg.copy()

        # Slight simulated sensor noise
        noise = np.random.normal(0, 1.5, frame.shape).astype(np.int16)
        frame_noisy = np.clip(frame.astype(np.int16) + noise, 0, 255).astype(np.uint8)
        frame = frame_noisy

        # Object 1: Moving rectangle (e.g., person walking across the room)
        # Active between frame 45 (1.5s) and 200 (~6.6s)
        if 45 <= frame_idx <= 200:
            progress = (frame_idx - 45) / (200 - 45)
            obj1_x = int(50 + progress * (width - 250))
            obj1_y = int(320 + np.sin(progress * np.pi * 4) * 15)  # slight bobbing walk motion
            obj1_w = 90
            obj1_h = 210

            # Draw "person" (shadow + body + head)
            # Soft shadow
            cv2.ellipse(frame, (obj1_x + obj1_w // 2, obj1_y + obj1_h + 5),
                        (55, 15), 0, 0, 360, (40, 40, 40), -1)
            # Torso & legs
            cv2.rectangle(frame, (obj1_x, obj1_y + 60), (obj1_x + obj1_w, obj1_y + obj1_h),
                          (40, 80, 180), -1)  # Blue outfit
            cv2.rectangle(frame, (obj1_x, obj1_y + 60), (obj1_x + obj1_w, obj1_y + obj1_h),
                          (20, 40, 100), 2)
            # Head
            cv2.circle(frame, (obj1_x + obj1_w // 2, obj1_y + 30), 26, (210, 180, 160), -1)
            cv2.circle(frame, (obj1_x + obj1_w // 2, obj1_y + 30), 26, (140, 110, 90), 2)

        # Object 2: Rolling / bouncing sphere
        # Active between frame 120 (4s) and 260 (~8.6s)
        if 120 <= frame_idx <= 260:
            progress2 = (frame_idx - 120) / (260 - 120)
            obj2_x = int((width - 150) - progress2 * 500)
            # Parabolic bouncing motion
            bounce = abs(np.sin(progress2 * np.pi * 3))
            obj2_y = int(620 - bounce * 160)
            radius = 35

            # Shadow on floor
            shadow_alpha_y = 640
            cv2.ellipse(frame, (obj2_x, shadow_alpha_y),
                        (int(radius * (1 - bounce * 0.4)), 10), 0, 0, 360, (45, 45, 45), -1)
            # Ball
            cv2.circle(frame, (obj2_x, obj2_y), radius, (50, 190, 80), -1)  # Green ball
            cv2.circle(frame, (obj2_x, obj2_y), radius, (20, 100, 40), 2)
            # Ball highlight
            cv2.circle(frame, (obj2_x - 10, obj2_y - 10), 8, (180, 255, 190), -1)

        # Embedded timecode on raw video
        seconds = frame_idx / fps
        timecode = f"REC 00:00:{int(seconds):02d}.{int((seconds % 1) * 100):02d}"
        cv2.putText(frame, timecode, (width - 250, 40),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 240), 2, cv2.LINE_AA)

        out.write(frame)

        if (frame_idx + 1) % 60 == 0 or frame_idx == total_frames - 1:
            print(f"  Progress: {frame_idx + 1}/{total_frames} frames ({int((frame_idx + 1)/total_frames * 100)}%)")

    out.release()
    print(f"[SUCCESS] Sample video generated successfully: {output_path}")
    return output_path

if __name__ == "__main__":
    out_file = sys.argv[1] if len(sys.argv) > 1 else "sample_input.mp4"
    generate_sample_video(out_file)
