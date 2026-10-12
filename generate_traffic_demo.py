"""
generate_traffic_demo.py
------------------------
Generates a realistic outdoor street / traffic surveillance test video ('demo_traffic.mp4').
Features:
  - 2-lane road with road markings and sidewalk
  - Moving vehicles (Red Sedan & Blue SUV) moving at different speeds
  - Crossing pedestrian
  - Timestamp and CAM-02 STREET CAMERA overlay
"""

import sys
import numpy as np
import cv2

def generate_traffic_demo(output_path="demo_traffic.mp4", duration_sec=8, fps=30, width=1280, height=720):
    total_frames = duration_sec * fps
    print(f"Generating realistic traffic demo video: '{output_path}' ({total_frames} frames)...")

    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

    if not out.isOpened():
        output_path = output_path.replace(".mp4", ".avi")
        fourcc = cv2.VideoWriter_fourcc(*'XVID')
        out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

    if not out.isOpened():
        print("Error: Could not open VideoWriter.")
        return None

    # Base background: Street scene
    base_bg = np.zeros((height, width, 3), dtype=np.uint8)

    # Top: Sky & distant buildings (0 to 220)
    base_bg[0:140, :] = (210, 190, 160)  # Pale sky
    # Distant buildings silhouettes
    for bx in range(0, width, 160):
        bh = np.random.RandomState(bx).randint(120, 200)
        cv2.rectangle(base_bg, (bx, 220 - bh), (bx + 140, 220), (120, 110, 105), -1)
        # Windows
        for wy in range(220 - bh + 20, 200, 25):
            for wx in range(bx + 15, bx + 125, 25):
                cv2.rectangle(base_bg, (wx, wy), (wx + 12, wy + 14), (220, 210, 170), -1)

    # Sidewalk (220 to 300)
    base_bg[220:300, :] = (160, 160, 165)
    # Curb
    base_bg[295:300, :] = (110, 110, 115)

    # Asphalt Road (300 to 650)
    base_bg[300:650, :] = (55, 55, 60)
    # White dashed lane divider at y=475
    for lx in range(0, width, 90):
        cv2.rectangle(base_bg, (lx, 470), (lx + 50, 480), (220, 220, 220), -1)

    # Pedestrian Crosswalk stripes (x = 350 to 470)
    for cy in range(310, 640, 36):
        cv2.rectangle(base_bg, (360, cy), (460, cy + 20), (240, 240, 240), -1)

    # Lower Sidewalk / Grass (650 to 720)
    base_bg[650:720, :] = (40, 110, 60)  # Green grass border

    # Street Lamp pole at x=200
    cv2.rectangle(base_bg, (196, 80), (204, 300), (90, 90, 90), -1)
    cv2.circle(base_bg, (200, 80), 16, (230, 230, 230), -1)

    # Street Camera Header
    cv2.putText(base_bg, "CAM-02 [NORTH INTERSECTION TRAFFIC]", (30, 45),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (240, 240, 240), 2, cv2.LINE_AA)

    print("Rendering frames...")
    for frame_idx in range(total_frames):
        frame = base_bg.copy()

        # Simulated sensor noise
        noise = np.random.normal(0, 1.2, (height, width, 3)).astype(np.int16)
        frame = np.clip(frame.astype(np.int16) + noise, 0, 255).astype(np.uint8)

        # Vehicle 1: Red Car (Left to Right in bottom lane, y=510)
        # Active between frame 30 (1.0s) and 160 (5.3s)
        if 30 <= frame_idx <= 160:
            p1 = (frame_idx - 30) / (160 - 30)
            car1_x = int(-200 + p1 * (width + 350))
            car1_y = 510
            car1_w, car1_h = 190, 85

            # Shadow
            cv2.ellipse(frame, (car1_x + car1_w // 2, car1_y + car1_h + 5),
                        (car1_w // 2 + 10, 16), 0, 0, 360, (25, 25, 25), -1)
            # Body (Red)
            cv2.rectangle(frame, (car1_x, car1_y + 30), (car1_x + car1_w, car1_y + car1_h), (30, 30, 200), -1)
            # Cabin
            pts = np.array([[car1_x + 35, car1_y + 30], [car1_x + 65, car1_y],
                            [car1_x + 140, car1_y], [car1_x + 165, car1_y + 30]], np.int32)
            cv2.fillPoly(frame, [pts], (20, 20, 180))
            # Windows
            cv2.rectangle(frame, (car1_x + 70, car1_y + 5), (car1_x + 135, car1_y + 26), (200, 230, 240), -1)
            # Headlights & Taillights
            cv2.circle(frame, (car1_x + car1_w - 4, car1_y + 50), 7, (220, 255, 255), -1)
            cv2.circle(frame, (car1_x + 4, car1_y + 50), 6, (0, 0, 220), -1)
            # Wheels
            cv2.circle(frame, (car1_x + 45, car1_y + car1_h), 18, (20, 20, 20), -1)
            cv2.circle(frame, (car1_x + car1_w - 45, car1_y + car1_h), 18, (20, 20, 20), -1)
            cv2.circle(frame, (car1_x + 45, car1_y + car1_h), 7, (180, 180, 180), -1)
            cv2.circle(frame, (car1_x + car1_w - 45, car1_y + car1_h), 7, (180, 180, 180), -1)

        # Vehicle 2: Blue SUV (Right to Left in top lane, y=340)
        # Active between frame 80 (2.6s) and 210 (7.0s)
        if 80 <= frame_idx <= 210:
            p2 = (frame_idx - 80) / (210 - 80)
            car2_x = int((width + 100) - p2 * (width + 300))
            car2_y = 350
            car2_w, car2_h = 170, 80

            # Shadow
            cv2.ellipse(frame, (car2_x + car2_w // 2, car2_y + car2_h + 4),
                        (car2_w // 2 + 8, 14), 0, 0, 360, (25, 25, 25), -1)
            # Body (Blue)
            cv2.rectangle(frame, (car2_x, car2_y + 25), (car2_x + car2_w, car2_y + car2_h), (180, 80, 20), -1)
            # Boxy SUV Roof
            cv2.rectangle(frame, (car2_x + 30, car2_y), (car2_x + 140, car2_y + 25), (150, 60, 15), -1)
            # Windows
            cv2.rectangle(frame, (car2_x + 38, car2_y + 4), (car2_x + 130, car2_y + 22), (210, 235, 245), -1)
            # Headlights (facing left)
            cv2.circle(frame, (car2_x + 4, car2_y + 45), 6, (220, 255, 255), -1)
            # Wheels
            cv2.circle(frame, (car2_x + 40, car2_y + car2_h), 16, (20, 20, 20), -1)
            cv2.circle(frame, (car2_x + car2_w - 40, car2_y + car2_h), 16, (20, 20, 20), -1)

        # Pedestrian walking across crosswalk (from y=260 down to y=640)
        # Active between frame 50 (1.6s) and 180 (6.0s)
        if 50 <= frame_idx <= 180:
            p3 = (frame_idx - 50) / (180 - 50)
            ped_x = 400 + int(np.sin(p3 * np.pi * 6) * 6)
            ped_y = int(270 + p3 * 340)
            ped_h = 75

            # Shadow
            cv2.ellipse(frame, (ped_x, ped_y + ped_h), (18, 6), 0, 0, 360, (30, 30, 30), -1)
            # Body (Yellow jacket)
            cv2.rectangle(frame, (ped_x - 12, ped_y + 22), (ped_x + 12, ped_y + 55), (30, 210, 230), -1)
            # Dark Pants
            cv2.rectangle(frame, (ped_x - 10, ped_y + 55), (ped_x + 10, ped_y + ped_h), (40, 40, 40), -1)
            # Head
            cv2.circle(frame, (ped_x, ped_y + 12), 10, (200, 170, 150), -1)

        # Timecode
        secs = frame_idx / fps
        timecode = f"REC 14:32:{int(secs):02d}.{int((secs % 1) * 100):02d}"
        cv2.putText(frame, timecode, (width - 240, 45),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 250), 2, cv2.LINE_AA)

        out.write(frame)

        if (frame_idx + 1) % 60 == 0 or frame_idx == total_frames:
            print(f"  Rendered {frame_idx + 1}/{total_frames} frames")

    out.release()
    print(f"[SUCCESS] Traffic demo video created: {output_path}")
    return output_path

if __name__ == "__main__":
    generate_traffic_demo()
