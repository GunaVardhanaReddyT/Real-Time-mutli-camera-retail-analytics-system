# Real-Time Multi-Camera Retail Analytics System

## High-Level Architecture

The Retail Analytics System captures and processes real-time video feeds from multiple cameras and provides actionable insights via a web dashboard and API endpoints. It is modular, scalable, and supports both local and distributed deployments.

### Architecture Overview
```
Input Layer: Camera feeds (USB/RTSP)
│
▼
Camera Manager: Manages multiple cameras with threaded VideoStreams
│
▼
Processing Pipeline: Detection (YOLOv8) → Tracking (SORT) → Analytics
│
▼
API Layer: FastAPI provides REST and WebSocket endpoints
│
▼
Presentation Layer: Web dashboard with real-time stats, video feeds, and charts
```

## Module Breakdown

### 1. Camera Module (`src/camera/`)

**VideoStream Class:**
- Threaded frame capture to prevent blocking
- Queue-based frame buffering
- Supports USB cameras, RTSP streams, and video files
- Configurable resolution and frame rate
- Async read support for FastAPI streaming

**CameraManager Class:**
- Manages multiple `CameraProcessor` instances
- Async processing loop for all cameras
- Lifecycle management (start/stop)
- Aggregates stats across all cameras

**CameraProcessor Class:**
- Orchestrates detection → tracking → analytics
- Annotates frames with bounding boxes, trails, and zones
- Encodes frames in base64 for web streaming

**Key Technologies:** OpenCV, threading, queue

### 2. Detection Module (`src/detection/`)

- Uses YOLOv8 (Ultralytics) for object detection
- Pre-trained on COCO dataset (person = class 0)
- Post-processing: Non-Maximum Suppression (NMS), confidence thresholding (default 0.5), class filtering
- **Output:** List of detections with bounding boxes, confidence, and class ID

**Key Technologies:** Ultralytics YOLOv8, COCO dataset

### 3. Tracking Module (`src/tracking/`)

- Implements SORT for multi-object tracking
- **Steps:**
  1. Prediction: Predict next positions of existing tracks
  2. Association: Hungarian algorithm for matching detections to tracks
  3. Update: Update matched tracks, create new tracks, remove old tracks

**Tracking Parameters:**  
- `max_age = 30` frames  
- `min_hits = 3` confirmations  
- `iou_threshold = 0.3`  

**Key Technologies:** SciPy (`linear_sum_assignment`), IOU metric

### 4. Analytics Module (`src/analytics/`)

- Zone analytics based on store layout
- Metrics per zone: current_count, total_entries, total_exits, average dwell time, peak count
- Heatmap generation:
  - Decays previous frame heatmap
  - Adds Gaussian blobs for each tracked position
- Metrics collector maintains time series data for footfall, counts, and aggregations

**Key Technologies:** NumPy  
**Zone Detection Algorithm:** Point-in-polygon (ray casting) method

### 5. API Module (`src/api/`)

**REST Endpoints:**
- `/api/health` → Health check
- `/api/cameras` → List all cameras
- `/api/cameras/{id}` → Camera details
- `/api/cameras/{id}/frame` → Latest frame
- `/api/cameras/{id}/heatmap` → Heatmap image
- `/api/stats` → Aggregated statistics
- `/api/zones` → Zone analytics

**WebSocket Endpoints:**
- `/api/ws/stream/{id}` → Real-time video feed
- `/api/ws/analytics` → Real-time analytics feed

**Static Files:**
- `/dashboard/*` → Web dashboard frontend files

## Concurrency & State Management

- **Main thread:** AsyncIO event loop running FastAPI and processing tasks
- **Camera threads:** One per camera for non-blocking frame capture
- **Frame queue:** Buffers frames to handle varying processing speeds
- **Async tasks:** Concurrent processing of multiple cameras and API requests

**Per Camera Processor State:**
- Current frame (`np.ndarray`)
- Frame queue
- Active tracks and track IDs
- Zone statistics
- Heatmap accumulator

**Global MetricsCollector:**
- Rolling time series for footfall and counts
- Aggregations for hourly footfall and peak occupancy
- Optional Redis support for distributed pub/sub, caching, and time-series persistence

## Technology Stack

| Layer              | Technology              | Purpose                                      |
|-------------------|------------------------|----------------------------------------------|
| Video Capture      | OpenCV                  | Camera interfacing and frame handling        |
| Detection          | YOLOv8 (Ultralytics)    | Real-time person detection                   |
| Tracking           | SORT + SciPy            | Multi-object tracking with Hungarian matching|
| Analytics          | NumPy                   | Zone analytics and heatmap generation        |
| API Server         | FastAPI + Uvicorn       | REST API and WebSocket server               |
| Serialization      | Pydantic                | Data validation and serialization           |
| Configuration      | PyYAML                  | YAML config parsing                          |
| Logging            | Loguru                  | Structured logging                           |
| Caching            | Redis (optional)        | Distributed caching                           |
| Frontend           | HTML/CSS/JS + Chart.js  | Real-time dashboard visualization            |
| Containerization   | Docker + Docker Compose | Deployment                                  |

## Scalability

- **Horizontal Scaling:** Multiple nodes process a subset of cameras and communicate via Redis Pub/Sub to a central aggregation service.
- **Vertical Scaling:** GPU acceleration with CUDA-enabled YOLOv8, optional TensorRT optimization, and batch frame processing for faster inference.

## Running the Project

```bash
# 1. Create project directory
mkdir retail-analytics && cd retail-analytics

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or: venv\Scripts\activate  # Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Create necessary directories
mkdir -p config logs dashboard/css dashboard/js

# 5. Run with Docker Compose (recommended)
docker-compose up --build

# OR run directly
python -m src.main
```
## Access Points

**Dashboard**: http://localhost:8000/dashboard

**API Docs**: http://localhost:8000/docs

**Health Check**: http://localhost:8000/api/health

## Future Enhancements

Face recognition for VIP customer detection

Product interaction analytics

Queue length estimation

Theft detection

Integration with POS systems
