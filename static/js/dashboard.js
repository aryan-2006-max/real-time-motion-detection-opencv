// static/js/dashboard.js
document.addEventListener('DOMContentLoaded', () => {
  // DOM Elements
  const dropZone = document.getElementById('dropZone');
  const videoFileInput = document.getElementById('videoFileInput');
  const browseBtn = document.getElementById('browseBtn');
  const uploadPlaceholder = document.getElementById('uploadPlaceholder');
  const fileLoadedState = document.getElementById('fileLoadedState');
  const loadedFileName = document.getElementById('loadedFileName');
  const loadedFileSize = document.getElementById('loadedFileSize');
  const clearFileBtn = document.getElementById('clearFileBtn');
  const useSampleBtn = document.getElementById('useSampleBtn');
  const useTrafficBtn = document.getElementById('useTrafficBtn');

  const methodSelect = document.getElementById('methodSelect');
  const minAreaSlider = document.getElementById('minAreaSlider');
  const minAreaVal = document.getElementById('minAreaVal');
  const blurSlider = document.getElementById('blurSlider');
  const blurVal = document.getElementById('blurVal');
  const threshSlider = document.getElementById('threshSlider');
  const threshVal = document.getElementById('threshVal');

  const startBtn = document.getElementById('startBtn');
  const navStatusIndicator = document.getElementById('navStatusIndicator');
  const navStatusText = document.getElementById('navStatusText');

  // Progress Section
  const progressSection = document.getElementById('progressSection');
  const progressStatusText = document.getElementById('progressStatusText');
  const progressPctText = document.getElementById('progressPctText');
  const progressBarFill = document.getElementById('progressBarFill');
  const telemetryFrame = document.getElementById('telemetryFrame');
  const telemetryFps = document.getElementById('telemetryFps');

  // Video Section
  const videoCompareSection = document.getElementById('videoCompareSection');
  const inputVideoPlayer = document.getElementById('inputVideoPlayer');
  const outputVideoPlayer = document.getElementById('outputVideoPlayer');
  const inputVideoTitle = document.getElementById('inputVideoTitle');

  // Analytics Section
  const analyticsSection = document.getElementById('analyticsSection');
  const statFrames = document.getElementById('statFrames');
  const statDuration = document.getElementById('statDuration');
  const statFps = document.getElementById('statFps');
  const statEvents = document.getElementById('statEvents');
  const statPeak = document.getElementById('statPeak');
  const statMaxArea = document.getElementById('statMaxArea');

  // Snapshots Section
  const snapshotsSection = document.getElementById('snapshotsSection');
  const snapshotsGrid = document.getElementById('snapshotsGrid');

  // State
  let activeFilename = null;
  let activeVideoUrl = null;
  let progressInterval = null;
  let motionChart = null;

  // Slider input updates
  minAreaSlider.addEventListener('input', (e) => {
    minAreaVal.textContent = `${e.target.value} px`;
  });
  blurSlider.addEventListener('input', (e) => {
    blurVal.textContent = e.target.value;
  });
  threshSlider.addEventListener('input', (e) => {
    threshVal.textContent = e.target.value;
  });

  // Browse Button
  browseBtn.addEventListener('click', (e) => {
    e.stopPropagation();
    videoFileInput.click();
  });
  dropZone.addEventListener('click', () => {
    if (!activeFilename) {
      videoFileInput.click();
    }
  });

  // Drag and drop
  ['dragenter', 'dragover'].forEach((eventName) => {
    dropZone.addEventListener(eventName, (e) => {
      e.preventDefault();
      e.stopPropagation();
      dropZone.classList.add('dragover');
    });
  });
  ['dragleave', 'drop'].forEach((eventName) => {
    dropZone.addEventListener(eventName, (e) => {
      e.preventDefault();
      e.stopPropagation();
      dropZone.classList.remove('dragover');
    });
  });
  dropZone.addEventListener('drop', (e) => {
    const files = e.dataTransfer.files;
    if (files.length > 0) {
      handleFileUpload(files[0]);
    }
  });

  videoFileInput.addEventListener('change', (e) => {
    if (e.target.files.length > 0) {
      handleFileUpload(e.target.files[0]);
    }
  });

  // File Upload Handler
  async function handleFileUpload(file) {
    const formData = new FormData();
    formData.append('video', file);

    uploadPlaceholder.classList.add('hidden');
    fileLoadedState.classList.remove('hidden');
    loadedFileName.textContent = `Uploading ${file.name}...`;
    loadedFileSize.textContent = formatBytes(file.size);
    startBtn.disabled = true;

    try {
      const res = await fetch('/api/upload', {
        method: 'POST',
        body: formData,
      });
      const data = await res.json();

      if (data.success) {
        activeFilename = data.filename;
        activeVideoUrl = data.url;
        loadedFileName.textContent = data.original_name;
        startBtn.disabled = false;
        setNavStatus('File Loaded', false);
      } else {
        alert(`Upload error: ${data.error}`);
        resetFileInput();
      }
    } catch (err) {
      alert(`Upload failed: ${err.message}`);
      resetFileInput();
    }
  }

  // Clear File
  clearFileBtn.addEventListener('click', (e) => {
    e.stopPropagation();
    resetFileInput();
  });

  function resetFileInput() {
    activeFilename = null;
    activeVideoUrl = null;
    videoFileInput.value = '';
    uploadPlaceholder.classList.remove('hidden');
    fileLoadedState.classList.add('hidden');
    startBtn.disabled = true;
    setNavStatus('System Idle', false);
  }

  // Quick Start Sample Video 1 (Indoor)
  useSampleBtn.addEventListener('click', async () => {
    useSampleBtn.disabled = true;
    useSampleBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Loading Demo 1...';

    try {
      const res = await fetch('/api/use_sample', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ type: 'indoor' }),
      });
      const data = await res.json();
      if (data.success) {
        activeFilename = data.filename;
        activeVideoUrl = data.url;

        uploadPlaceholder.classList.add('hidden');
        fileLoadedState.classList.remove('hidden');
        loadedFileName.textContent = data.label || 'sample_input.mp4';
        loadedFileSize.textContent = '~1.0 MB';

        startBtn.disabled = false;
        setNavStatus('Demo 1 Ready', false);
      }
    } catch (err) {
      alert(`Error loading sample: ${err.message}`);
    } finally {
      useSampleBtn.disabled = false;
      useSampleBtn.innerHTML = '<i class="fa-solid fa-person-walking"></i> Demo 1: Indoor Reception Camera (sample_input.mp4)';
    }
  });

  // Quick Start Sample Video 2 (Traffic)
  useTrafficBtn.addEventListener('click', async () => {
    useTrafficBtn.disabled = true;
    useTrafficBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Loading Demo 2...';

    try {
      const res = await fetch('/api/use_sample', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ type: 'traffic' }),
      });
      const data = await res.json();
      if (data.success) {
        activeFilename = data.filename;
        activeVideoUrl = data.url;

        uploadPlaceholder.classList.add('hidden');
        fileLoadedState.classList.remove('hidden');
        loadedFileName.textContent = data.label || 'demo_traffic.mp4';
        loadedFileSize.textContent = '~1.9 MB';

        startBtn.disabled = false;
        setNavStatus('Demo 2 Ready', false);
      }
    } catch (err) {
      alert(`Error loading traffic demo: ${err.message}`);
    } finally {
      useTrafficBtn.disabled = false;
      useTrafficBtn.innerHTML = '<i class="fa-solid fa-car-side"></i> Demo 2: Street Traffic Camera (demo_traffic.mp4)';
    }
  });

  // Start Motion Detection Processing
  startBtn.addEventListener('click', async () => {
    if (!activeFilename) return;

    // UI state updates
    startBtn.disabled = true;
    useSampleBtn.disabled = true;
    useTrafficBtn.disabled = true;
    setNavStatus('Processing Video...', true);

    progressSection.classList.remove('hidden');
    videoCompareSection.classList.add('hidden');
    analyticsSection.classList.add('hidden');
    snapshotsSection.classList.add('hidden');

    progressBarFill.style.width = '0%';
    progressPctText.textContent = '0%';
    progressStatusText.textContent = 'Initializing computer vision pipeline...';

    const payload = {
      filename: activeFilename,
      method: methodSelect.value,
      min_area: parseInt(minAreaSlider.value, 10),
      blur_kernel: parseInt(blurSlider.value, 10),
      threshold_val: parseInt(threshSlider.value, 10),
    };

    try {
      const res = await fetch('/api/process', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      const data = await res.json();

      if (!data.success) {
        alert(`Error starting processing: ${data.error}`);
        startBtn.disabled = false;
        useSampleBtn.disabled = false;
        useTrafficBtn.disabled = false;
        setNavStatus('System Idle', false);
        progressSection.classList.add('hidden');
        return;
      }

      if (data.serverless) {
        progressBarFill.style.width = '100%';
        progressPctText.textContent = '100%';
        progressStatusText.textContent = 'Completed! Loading telemetry & results...';
        setTimeout(loadResults, 500);
        return;
      }

      // Start Polling progress
      startPollingProgress();
    } catch (err) {
      alert(`Request failed: ${err.message}`);
      startBtn.disabled = false;
      useSampleBtn.disabled = false;
      useTrafficBtn.disabled = false;
      setNavStatus('System Idle', false);
    }
  });

  // Progress Poller
  function startPollingProgress() {
    if (progressInterval) clearInterval(progressInterval);

    progressInterval = setInterval(async () => {
      try {
        const res = await fetch('/api/progress');
        const state = await res.json();

        const pct = state.progress;
        progressBarFill.style.width = `${pct}%`;
        progressPctText.textContent = `${pct}%`;
        telemetryFrame.textContent = `${state.frame_idx} / ${state.total_frames}`;
        telemetryFps.textContent = `${state.current_fps} FPS`;

        if (pct < 100 && state.is_processing) {
          progressStatusText.textContent = `Analyzing motion frame ${state.frame_idx} of ${state.total_frames}...`;
        }

        if (state.status === 'completed' || (!state.is_processing && pct >= 100)) {
          clearInterval(progressInterval);
          progressInterval = null;
          progressStatusText.textContent = 'Processing complete! Finalizing output video...';
          setTimeout(loadResults, 800);
        } else if (state.status === 'error') {
          clearInterval(progressInterval);
          progressInterval = null;
          alert(`Processing error: ${state.error_message}`);
          startBtn.disabled = false;
          useSampleBtn.disabled = false;
          setNavStatus('Error Occurred', false);
        }
      } catch (err) {
        console.error('Progress poll failed:', err);
      }
    }, 250);
  }

  // Load and Render Results
  async function loadResults() {
    try {
      const res = await fetch('/api/results');
      const data = await res.json();

      setNavStatus('Completed', false);
      startBtn.disabled = false;
      useSampleBtn.disabled = false;
      useTrafficBtn.disabled = false;
      progressSection.classList.add('hidden');

      // 1. Video Comparison Player
      videoCompareSection.classList.remove('hidden');
      inputVideoTitle.textContent = loadedFileName.textContent;
      inputVideoPlayer.src = data.input_video_url;
      outputVideoPlayer.src = data.output_video_url;

      // 2. Metrics & Stats
      analyticsSection.classList.remove('hidden');
      const m = data.metrics;
      statFrames.textContent = m.total_frames;
      statDuration.textContent = `${m.duration_sec}s`;
      statFps.textContent = `${m.avg_fps} FPS`;
      statEvents.textContent = m.total_events;
      statPeak.textContent = m.peak_objects;
      statMaxArea.textContent = `${m.max_motion_area.toLocaleString()} px`;

      // 3. Render Chart.js Analytics
      renderMotionChart(data.chart_data);

      // 4. Snapshots Gallery
      snapshotsSection.classList.remove('hidden');
      snapshotsGrid.innerHTML = '';
      if (data.snapshots && data.snapshots.length > 0) {
        data.snapshots.forEach((snapUrl, idx) => {
          const card = document.createElement('div');
          card.className = 'snapshot-card';
          const filename = snapUrl.split('/').pop();
          card.innerHTML = `
            <a href="${snapUrl}" target="_blank" title="Click to view full size">
              <img src="${snapUrl}" alt="Motion Snapshot ${idx + 1}" class="snapshot-img" loading="lazy">
            </a>
            <div class="snapshot-info">
              <span class="snapshot-tag">Event #${idx + 1}</span>
              <span class="snapshot-time">${filename.replace('motion_event_', '').replace('.jpg', '')}</span>
            </div>
          `;
          snapshotsGrid.appendChild(card);
        });
      } else {
        snapshotsGrid.innerHTML = '<p style="color: var(--text-muted); grid-column: 1/-1;">No motion exceeded threshold to trigger snapshots.</p>';
      }

      // Scroll smoothly to video section
      videoCompareSection.scrollIntoView({ behavior: 'smooth' });
    } catch (err) {
      alert(`Error loading results: ${err.message}`);
    }
  }

  // Chart.js Timeline Renderer
  function renderMotionChart(chartData) {
    const ctx = document.getElementById('motionChart').getContext('2d');

    if (motionChart) {
      motionChart.destroy();
    }

    const labels = chartData.timestamps.map((t) => `${t}s`);
    const objectCounts = chartData.object_counts;
    const areas = chartData.motion_areas;

    motionChart = new Chart(ctx, {
      type: 'line',
      data: {
        labels: labels,
        datasets: [
          {
            label: 'Moving Targets Count',
            data: objectCounts,
            borderColor: '#EF4444',
            backgroundColor: 'rgba(239, 68, 68, 0.15)',
            borderWidth: 2,
            tension: 0.3,
            fill: true,
            yAxisID: 'y',
            pointRadius: 2,
          },
          {
            label: 'Motion Area (px)',
            data: areas,
            borderColor: '#06B6D4',
            backgroundColor: 'transparent',
            borderWidth: 1.5,
            borderDash: [5, 5],
            tension: 0.3,
            yAxisID: 'y1',
            pointRadius: 0,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: {
          mode: 'index',
          intersect: false,
        },
        plugins: {
          legend: {
            labels: { color: '#CBD5E1', font: { family: 'Inter', size: 12 } },
          },
          tooltip: {
            backgroundColor: '#1E293B',
            titleColor: '#FFFFFF',
            bodyColor: '#CBD5E1',
            borderColor: '#334155',
            borderWidth: 1,
          },
        },
        scales: {
          x: {
            grid: { color: 'rgba(51, 65, 85, 0.3)' },
            ticks: { color: '#94A3B8', maxTicksLimit: 12 },
          },
          y: {
            type: 'linear',
            display: true,
            position: 'left',
            title: { display: true, text: 'Target Count', color: '#EF4444' },
            grid: { color: 'rgba(51, 65, 85, 0.3)' },
            ticks: { color: '#94A3B8', stepSize: 1 },
            min: 0,
          },
          y1: {
            type: 'linear',
            display: true,
            position: 'right',
            title: { display: true, text: 'Motion Area (px)', color: '#06B6D4' },
            grid: { drawOnChartArea: false },
            ticks: { color: '#94A3B8' },
            min: 0,
          },
        },
      },
    });
  }

  // Helpers
  function setNavStatus(text, isBusy) {
    navStatusText.textContent = text;
    if (isBusy) {
      navStatusIndicator.classList.add('busy');
    } else {
      navStatusIndicator.classList.remove('busy');
    }
  }

  function formatBytes(bytes, decimals = 1) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const dm = decimals < 0 ? 0 : decimals;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
  }
});
