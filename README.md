# Real-Time Motion Detection System using OpenCV

A computer vision project that detects motion in real-time from video files or live webcam feeds. Built with Python and OpenCV, the system highlights moving objects with bounding boxes, provides a live Heads-Up Display (HUD), exports an annotated output video, logs motion events to CSV, and captures motion snapshots.

---

## 🌟 Key Features

- **Multi-Source Video Input**: Supports video files (`.mp4`, `.avi`, `.mov`, `.mkv`), live webcam streams (`0`), or synthetic test videos.
- **Accurate Motion Detection Pipeline**:
  - **Grayscale Conversion & Gaussian Blur**: Suppresses sensor noise and high-frequency jitter.
  - **Background Modeling**:
    - *Accumulative Running Average*: Adapts dynamically to gradual ambient light changes.
    - *MOG2 Subtractor*: Gaussian Mixture Model background subtraction with shadow filtering.
  - **Morphological Dilation**: Fills gaps and holes inside detected moving contours.
  - **Area-Based Filtering**: Distinguishes actual moving entities from camera noise, insects, or leaf flicker.
- **Visual Heads-Up Display (HUD)**:
  - Red / Green dynamic status banner (`MOTION DETECTED` vs `NO MOTION`).
  - Active object target bounding boxes, IDs, and pixel area metrics.
  - Real-time FPS counter and timestamp display.
- **2x2 Multi-View Dashboard**:
  - Toggle live between single view and a 4-pane diagnostic comparison (Raw Feed, Gaussian Blur, Motion Mask, Final Annotated).
- **Automated Output Generation**:
  - Encodes and saves the complete processed video to an output file (`output_detected.mp4`).
  - Records continuous motion intervals and peak object counts into `motion_events.csv`.
  - Saves high-resolution snapshot images into `snapshots/` upon motion trigger.
- **Synthetic Test Video Generator**: Included out-of-the-box so you can test immediately without searching for external videos.

---

## 📁 Project Structure

```
c:\MAD\
├── requirements.txt            # Python dependencies (opencv-python, numpy)
├── main.py                     # Main application entry point (CLI & interactive menu)
├── generate_sample_video.py    # Generates synthetic 720p sample video for testing
├── README.md                   # Project documentation and guide
└── src/
    ├── __init__.py             # Package init
    ├── detector.py             # Computer Vision engine (MotionDetector)
    ├── visualizer.py           # HUD overlays, bounding boxes, and 2x2 dashboard
    └── recorder.py             # VideoWriter, CSV logger, and SnapshotManager
```

---

## 🚀 Installation & Quick Start

### 1. Install Dependencies

Ensure Python 3.8+ is installed, then install required packages:

```powershell
pip install -r requirements.txt
```

### 2. Generate Sample Video (Optional)

If you do not have an input video ready, generate a synthetic 10-second test video:

```powershell
python generate_sample_video.py
```
This generates `sample_input.mp4` containing realistic movement patterns and static phases.

### 3. Run the System

#### 🌐 Option A: Interactive Web Dashboard (Recommended)
Launch the modern browser-based GUI dashboard:
```powershell
python app.py
```
Open **[http://127.0.0.1:5000](http://127.0.0.1:5000)** in your browser to:
- Drag-and-drop any input video or use the built-in sample video.
- Adjust motion detection parameters (algorithm, min-area, blur, threshold).
- Watch real-time processing progress and telemetry.
- Compare the input video and motion-detected output side-by-side.
- Inspect the interactive Chart.js motion activity timeline and snapshot gallery.
- Download the processed output video and CSV event logs with one click.

#### 🖥️ Option B: Terminal Interactive Mode
Run the script without arguments for an interactive command-line menu:
```powershell
python main.py
```

#### 📁 Option C: Specify an Input Video File
```powershell
python main.py --input sample_input.mp4 --output output_detected.mp4
```

#### 📹 Option D: Live Webcam Mode
```powershell
python main.py --input 0
```

#### ⚡ Option E: Headless / Background Processing
To process a video file without displaying a GUI window (e.g. for batch processing or servers):
```powershell
python main.py --input sample_input.mp4 --no-display
```

---

## 🎮 Interactive Keyboard Controls

While the video playback window is active:

| Key | Action |
|:---:|:---|
| **`q`** | **Quit** and finalize output video & CSV log |
| **`p`** | **Pause / Resume** video playback |
| **`m`** | **Toggle Multi-View** (Switch between single view and 2x2 diagnostic grid) |
| **`s`** | **Save Manual Snapshot** immediately to `snapshots/` |

---

## ⚙️ Command-Line Arguments

| Flag | Long Option | Default | Description |
|---|---|---|---|
| `-i` | `--input` | `None` | Path to input video or webcam index (`0`) |
| `-o` | `--output` | `output_detected.mp4` | Path to save output video |
| `-a` | `--min-area` | `1200` | Minimum contour area (px) to count as motion |
| `-m` | `--method` | `accumulative` | Algorithm: `accumulative` or `mog2` |
| | `--multi-view` | `False` | Start directly in 2x2 multi-view comparison mode |
| | `--no-display` | `False` | Run in headless mode without opening GUI window |
| | `--log` | `motion_events.csv` | Path for CSV motion event timeline |

---

## 🔬 Mathematical & Computer Vision Pipeline

```
Input Frame (BGR)
       │
       ▼
Grayscale Conversion: Y = 0.299*R + 0.587*G + 0.114*B
       │
       ▼
Gaussian Blur Filter: G(x,y) convolution with 21x21 kernel (removes high-frequency sensor noise)
       │
       ▼
Background Modeling:
  • Accumulative Running Average: B_t = (1 - α) * B_{t-1} + α * I_t
  • Frame Delta: Δ = |I_t - B_t|
       │
       ▼
Binary Thresholding: T(x,y) = 255 if Δ(x,y) > θ else 0
       │
       ▼
Morphological Dilation: Fills internal holes in foreground masks
       │
       ▼
Contour Extraction & Area Filter: Area(c) ≥ min_area
       │
       ▼
Visual HUD & Bounding Rectangles → VideoWriter & CSV Event Log
```

---

## 📊 Output Files

1. **Annotated Video (`output_detected.mp4`)**:
   Full video with dynamic bounding boxes, target IDs, centroid indicators, and HUD telemetry.
2. **Event Log (`motion_events.csv`)**:
   Structured log containing:
   - `Event_ID`: Sequential event index
   - `Start_Time_Sec`: Timestamp when movement began
   - `End_Time_Sec`: Timestamp when movement stopped
   - `Duration_Sec`: Length of movement
   - `Peak_Object_Count`: Maximum simultaneous moving objects
   - `Max_Motion_Area_Px`: Peak moving area in pixels
3. **Snapshots (`snapshots/`)**:
   Timestamped JPEG frames captured automatically when motion begins.
