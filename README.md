# UAV Telemetry Analyzer

![Python](https://img.shields.io/badge/Python-3.11+-blue?style=flat-square&logo=python)
![Streamlit](https://img.shields.io/badge/Streamlit-1.56-red?style=flat-square&logo=streamlit)
![Gemini](https://img.shields.io/badge/Gemini-2.5_Flash-orange?style=flat-square&logo=google)
![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)

Web application for automated analysis of Ardupilot flight controller binary logs (`.BIN`) with 3D trajectory visualization, flight metric computation and AI-powered diagnostics.

---

## 🚀 Recent Updates (Final Engineering Grade)

- **Advanced IMU Integration:** Implemented full **Tilt Compensation** using a Rotation Matrix (Roll/Pitch) to rotate acceleration vectors into the Earth Frame.
- **KML Export:** Added one-click export to **Google Earth (.kml)** with 3D path extrusion.
- **Verification Dashboard:** New chart comparing **GPS vs IMU vertical speed** to visually prove mathematical accuracy.
- **Optimized UI:** Re-branded sidebar with a custom logo, zero-padding for maximum screen space, and improved ergonomics.
- **Honest Data Engine:** Removed aggressive filtering to ensure 100% telemetry integrity for crash analysis.

---

## Table of Contents

1. [Overview](#overview)
2. [Quick Start](#quick-start)
3. [Configuration](#configuration)
4. [Project Structure](#project-structure)
5. [How It Works](#how-it-works)
   - [Log Parsing & Sensor Sync](#log-parsing--sensor-sync)
   - [Coordinate Systems](#coordinate-systems)
   - [Flight Metrics & Tilt Compensation](#flight-metrics--tilt-compensation)
   - [3D Visualization](#3d-visualization)
   - [AI Analysis](#ai-analysis)
   - [Pipeline Logging](#pipeline-logging)
6. [Theoretical Grounding](#theoretical-grounding)
7. [Stack & Rationale](#stack--rationale)
8. [Docker Deployment](#docker-deployment)
9. [Tests](#tests)

---

## Overview

Ardupilot flight controllers record every sensor reading into binary `.BIN` log files (DataFlash format). These files contain GPS coordinates, IMU accelerometer/gyroscope data, barometer readings, flight modes, and dozens of other message types — all timestamped in microseconds.

Manually analyzing these files requires specialized tools and deep domain knowledge. This application automates the entire pipeline:

```
.BIN file  →  Parse  →  Sync Sensors  →  Compute Metrics  →  3D Visualization  →  AI Report
```

The result is a web dashboard where you upload a log file and immediately get a full flight analysis — trajectory, metrics, charts, map and an AI-generated technical report.

---

## Quick Start

### Requirements

- Python 3.11+
- pip

### Local setup

```bash
# 1. Clone the repository
git clone https://github.com/Illia915/BEST-selection_project.git
cd BEST-selection_project

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment
cp .env.example .env
# Open .env and add your GEMINI_API_KEY (see Configuration section)

# 4. Run
streamlit run app.py
```

Open `http://localhost:8501` in your browser.

### Using the app

1. **Upload a log** — drag and drop a `.BIN` file into the sidebar uploader, or click "Load Sample File" to use one of the included test logs from the `data/` folder.
2. **Explore metrics** — the top panel shows 8 key flight metrics computed automatically.
3. **View trajectory** — the **3D Trajectory** tab shows the flight path in 3D space, colored by speed or time.
4. **View map** — the **Map** tab shows the flight on an OpenStreetMap tile layer with speed-based color coding.
5. **View charts** — the **Charts** tab shows altitude and speed over time, plus the raw GPS data table.
6. **Run AI analysis** — enter your Gemini API key in the sidebar, choose a model (or enable A/B comparison), and click **Run Analysis**.

---

## Configuration

All configuration is done via environment variables. Copy `.env.example` to `.env` and fill in the values:

```env
# ── AI ──────────────────────────────────────────────────────────────────────
GEMINI_API_KEY=AIza...
GEMINI_MODEL=gemini-2.5-flash

# ── Logging ──────────────────────────────────────────────────────────────────
LOG_AI_PIPELINE=true
LOG_STORAGE=local

# ── MongoDB (optional) ───────────────────────────────────────────────────────
MONGO_URI=mongodb://localhost:27017
MONGO_DB=uav_telemetry
```

---

## Project Structure

```
.
├── app.py                      # Streamlit UI — layout, state, all tabs
├── Dockerfile                  # Container image for the app
├── scraper/
│   └── dataflash.py            # Ardupilot .BIN parser + sensor extraction
├── analytics/
│   ├── metrics.py              # Haversine, trapezoidal integration, tilt compensation
│   └── coords.py               # WGS-84 → ECEF → ENU coordinate conversion
├── visualization/
│   ├── plot3d.py               # 3D Plotly trajectory + charts
│   └── map_view.py             # Folium/Leaflet interactive 2D map
├── ai/                         # LLM diagnostics and pipeline logging
└── data/                       # Sample log files for testing
```

---

## How It Works

### Log Parsing & Sensor Sync

Ardupilot saves flight data in **DataFlash binary format**. `scraper/dataflash.py` uses **pymavlink** to decode this format:

- **GPS messages** — Latitude, Longitude, Altitude, Ground Speed.
- **IMU messages** — Raw acceleration (AccX/Y/Z) at high frequency (100+ Hz).
- **ATT messages** — Vehicle attitude (Roll, Pitch, Yaw) used for orientation.

**Sensor Synchronization:** Since IMU and Attitude are recorded at different rates, the system uses a **Time-based Join (`merge_asof`)** to align orientation data with every accelerometer reading for precise tilt compensation.

### Coordinate Systems

The app works with three coordinate systems:
1. **WGS-84**: Global GPS standard (degrees).
2. **ECEF**: Earth-Centered, Earth-Fixed 3D Cartesian system.
3. **ENU (East-North-Up)**: Local Cartesian system centered on the takeoff point.axes are in meters from the start position. 

The full pipeline: GPS point → WGS-84 → ECEF → ENU. The 3D plot uses ENU coordinates directly.

### Flight Metrics & Tilt Compensation

**Total distance** uses the **Haversine formula**, which calculates the great-circle distance between two points on a sphere, accounting for Earth's curvature.

**Ideal Vertical Speed (Tilt Compensation)**:
Standard IMU integration of the raw Z-axis is inaccurate because gravity ($g$) shifts between axes as the drone tilts. We implement **Body Frame to Earth Frame rotation**:
```python
acc_z_earth = ax*sin(-pitch) + ay*sin(roll)*cos(pitch) + az*cos(roll)*cos(pitch)
acc_z_pure = acc_z_earth + 9.80665
```
By rotating the acceleration vector back to the "global vertical" before integrating, we get a truer vertical velocity even during aggressive maneuvers.

**Dynamic Acceleration**:
Calculated as the magnitude of the 3D acceleration vector minus the gravity constant:
`dynamic_acc = |√(AccX² + AccY² + AccZ²) - 9.80665|`. We use the **95th percentile** to filter out single-sample noise spikes.

---

## Theoretical Grounding

### 1. Coordinate Transformations (WGS-84 → ENU)
Global coordinates are non-Cartesian. To visualize them in 3D and perform metric calculations, we convert them to a local **East-North-Up (ENU)** system. This ensures that X/Y/Z axes represent real meters relative to the takeoff point.

### 2. IMU Integration (Trapezoidal Method)
To derive velocity from acceleration, we implement the **trapezoidal rule**:
`v[i] = v[i−1] + (a[i−1] + a[i]) / 2 · Δt`
This method is $O(dt^2)$ accurate, providing a much smoother and more precise velocity curve compared to the basic rectangular method.

### 3. Orientation: Euler Angles vs Quaternions
The system uses **Attitude (Roll, Pitch, Yaw)** to rotate the acceleration vector. 
- **Gimbal Lock**: Euler angles suffer from "Gimbal Lock" at 90° pitch. For advanced aerobatics, **Quaternions** are superior as they avoid singularities and are more computationally efficient.

### 4. IMU Sensor Drift
Integrating noisy IMU data is an "open-loop" process. Small measurement biases lead to **linear error growth** in velocity and **quadratic growth** in position. This is why long-term stability requires GPS fusion (EKF).

---

## Stack & Rationale

| Library | Why this one |
|---|---|
| **pymavlink** | The only library that correctly decodes all DataFlash format versions. |
| **pandas** | Natural fit for tabular telemetry; used for high-speed sensor synchronization. |
| **numpy** | Vectorized math for coordinate transforms and tilt compensation. |
| **plotly** | Best Python library for interactive 3D charts in the browser. |
| **folium** | Leaflet maps in Python without an API key requirement. |
| **streamlit** | Fastest path from Python analysis code to a working web UI. |

---

## Docker Deployment

```bash
# Build and start
cp .env.example .env
docker-compose up --build
```
The `docker-compose.yml` spins up the **Streamlit app** and a **MongoDB** instance for AI pipeline logging.

---

## Tests

```bash
# Full metrics and coordinate conversion smoke test
python tests/test_parser.py
```
This test parses `data/00000001.BIN`, checks ENU ranges, and prints all computed metrics including the ideal IMU velocity and dynamic acceleration.
