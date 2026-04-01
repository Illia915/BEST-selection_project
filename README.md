# UAV Telemetry Analyzer

![Python](https://img.shields.io/badge/Python-3.11+-blue?style=flat-square&logo=python)
![Streamlit](https://img.shields.io/badge/Streamlit-1.56-red?style=flat-square&logo=streamlit)
![Gemini](https://img.shields.io/badge/Gemini-2.5_Flash-orange?style=flat-square&logo=google)
![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)

Web application for automated analysis of Ardupilot flight controller binary logs (`.BIN`) with 3D trajectory visualization, flight metric computation and AI-powered diagnostics.

---

## Table of Contents

1. [Overview](#overview)
2. [Quick Start](#quick-start)
3. [Configuration](#configuration)
4. [Project Structure](#project-structure)
5. [How It Works](#how-it-works)
   - [Log Parsing](#log-parsing)
   - [Coordinate Systems](#coordinate-systems)
   - [Flight Metrics](#flight-metrics)
   - [3D Visualization](#3d-visualization)
   - [AI Analysis](#ai-analysis)
   - [Pipeline Logging](#pipeline-logging)
6. [Stack & Rationale](#stack--rationale)
7. [Docker Deployment](#docker-deployment)
8. [Tests](#tests)

---

## Overview

Ardupilot flight controllers record every sensor reading into binary `.BIN` log files (DataFlash format). These files contain GPS coordinates, IMU accelerometer/gyroscope data, barometer readings, flight modes, and dozens of other message types — all timestamped in microseconds.

Manually analyzing these files requires specialized tools and deep domain knowledge. This application automates the entire pipeline:

```
.BIN file  →  Parse  →  Filter noise  →  Compute metrics  →  3D visualization  →  AI report
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

1. **Upload a log** — drag and drop a `.BIN` file into the sidebar uploader, or click "Load Sample File" to use one of the included test logs from the `data/` folder
2. **Explore metrics** — the top panel shows 8 key flight metrics computed automatically
3. **View trajectory** — the **3D Trajectory** tab shows the flight path in 3D space, colored by speed or time. Use the sidebar radio to switch coloring modes
4. **View map** — the **Map** tab shows the flight on an OpenStreetMap tile layer with speed-based color coding
5. **View charts** — the **Charts** tab shows altitude and speed over time, plus the raw GPS data table
6. **Run AI analysis** — enter your Gemini API key in the sidebar, choose a model (or enable A/B comparison), and click **Run Analysis**

---

## Configuration

All configuration is done via environment variables. Copy `.env.example` to `.env` and fill in the values:

```env
# ── AI ──────────────────────────────────────────────────────────────────────
# Free Gemini API key from https://aistudio.google.com/app/apikey
GEMINI_API_KEY=AIza...

# Default model to use for analysis
# Options: gemini-2.5-flash | gemini-2.5-flash-lite | gemini-2.5-pro
GEMINI_MODEL=gemini-2.5-flash

# ── Logging ──────────────────────────────────────────────────────────────────
# Set to "true" to log every AI request (prompt, response, tokens, metrics)
LOG_AI_PIPELINE=true

# Where to store logs: "local" (JSON files in logs/) or "mongodb"
LOG_STORAGE=local

# ── MongoDB (only used when LOG_STORAGE=mongodb) ─────────────────────────────
MONGO_URI=mongodb://localhost:27017
MONGO_DB=uav_telemetry
```

**Getting a Gemini API key:**
1. Go to [aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey)
2. Sign in with a Google account
3. Click **Create API key**
4. Copy the key (starts with `AIza...`) into `.env` or paste it directly in the app sidebar

The key is free and has a generous rate limit for development use. You can also paste the key directly in the app sidebar without setting up `.env` at all.

---

## Project Structure

```
.
├── app.py                      # Streamlit UI — layout, state, all tabs
├── Dockerfile                  # Container image for the app
├── docker-compose.yml          # App + MongoDB service
├── requirements.txt            # Python dependencies
├── .env.example                # Environment variable reference
│
├── scraper/
│   └── dataflash.py            # Ardupilot .BIN parser via pymavlink
│                               # Outputs dict[str, pd.DataFrame]
│
├── analytics/
│   ├── metrics.py              # Haversine, trapezoidal integration,
│   │                           # sampling rate detection, GPS noise filtering
│   └── coords.py               # WGS-84 → ECEF → ENU coordinate conversion
│
├── visualization/
│   ├── plot3d.py               # 3D Plotly trajectory + altitude/speed charts
│   └── map_view.py             # Folium/Leaflet interactive 2D map
│
├── ai/
│   ├── assistant.py            # analyze_flight(), analyze_flight_ab()
│   ├── prompts.py              # Gemini prompt templates
│   ├── token_counter.py        # Session token usage tracking
│   └── pipeline_logger.py      # JSON / MongoDB request logging
│
├── data/
│   ├── 00000001.BIN            # Sample log 1 (short flight, Canberra SITL)
│   └── 00000019.BIN            # Sample log 2 (longer flight)
│
├── logs/                       # AI pipeline JSON logs — git-ignored
└── tests/
    ├── test_parser.py          # Manual scraper + metrics smoke test
    └── test_mavlink.py         # Raw pymavlink message type dump
```

---

## How It Works

### Log Parsing

Ardupilot saves flight data in **DataFlash binary format** — a proprietary binary format where each message type (GPS, IMU, ATT, BARO, etc.) has a schema defined in `FMT` messages at the start of the file.

`scraper/dataflash.py` uses **pymavlink** — the official Ardupilot Python library — to decode this format:

```
.BIN file
    └── FMT messages   → defines field names and types for each message type
    └── GPS messages   → Lat, Lng, Alt, Spd, VZ, TimeUS, ...
    └── IMU messages   → AccX, AccY, AccZ, GyrX, GyrY, GyrZ, TimeUS, ...
    └── ATT, BARO, ... → hundreds of other message types
```

Each message type is collected into a list of dicts and then converted to a `pandas.DataFrame`. The function returns a `dict[str, DataFrame]` — one DataFrame per message type found in the log.

Column names are normalized because different Ardupilot firmware versions use slightly different field names (e.g., `Lat` vs `latitude`, `Spd` vs `speed`).

**Sampling rate detection** (`analytics/metrics.py → compute_sampling_rate`): The parser automatically computes the mean sampling frequency for GPS and IMU by averaging the time deltas between consecutive `TimeUS` timestamps. Results are displayed in the dashboard header next to the metrics (e.g., `GPS 5.0 Hz · IMU 100.0 Hz`). Typical values for Ardupilot: GPS 5–10 Hz, IMU 100–400 Hz.

**GPS noise filtering** (`analytics/metrics.py → filter_gps`): Raw GPS logs often contain invalid readings — altitude going hundreds of meters below the takeoff point, coordinates jumping across the map. Two filters are applied before computing metrics:
- Drop points where altitude is more than 200 m below the starting altitude
- Drop points where lat/lng deviates more than 0.5° from the median (removes teleportation glitches)

---

### Coordinate Systems

The app works with three coordinate systems:

**WGS-84** — the global GPS standard. Coordinates are latitude (degrees), longitude (degrees), and altitude (meters above the ellipsoid). This is what GPS receivers output. WGS-84 cannot be used directly for distance or geometry because degrees have different metric lengths depending on latitude.

**ECEF** (Earth-Centered, Earth-Fixed) — a 3D Cartesian system with origin at Earth's center. X points through the Gulf of Guinea (0°lat, 0°lon), Z points to the North Pole. Used as an intermediate step.

Conversion formula (`analytics/coords.py → wgs84_to_ecef`):
```
N(φ) = a / √(1 − e²·sin²(φ))      ← radius of curvature
X = (N + h) · cos(φ) · cos(λ)
Y = (N + h) · cos(φ) · sin(λ)
Z = (N·(1−e²) + h) · sin(φ)
```
where `a = 6 378 137.0 m` (WGS-84 semi-major axis), `e² = 0.006694` (eccentricity²).

**ENU** (East-North-Up) — a local Cartesian system centered on the takeoff point. East (X), North (Y), Up (Z) axes are in meters from the start position. This is ideal for visualization because axes are intuitive and units are meters.

Conversion from ECEF to ENU uses a rotation matrix derived from the takeoff point coordinates (`analytics/coords.py → ecef_to_enu`):
```
| E |   | −sin(λ)          cos(λ)         0      |   | dx |
| N | = | −sin(φ)cos(λ)  −sin(φ)sin(λ)  cos(φ)  | × | dy |
| U |   |  cos(φ)cos(λ)   cos(φ)sin(λ)  sin(φ)  |   | dz |
```

The full pipeline: GPS point → WGS-84 → ECEF → ENU. The 3D plot uses ENU coordinates directly — X = East (m), Y = North (m), Z = Up (m).

---

### Flight Metrics

All metrics are computed in `analytics/metrics.py`.

**Total distance** uses the **Haversine formula**, which calculates the great-circle distance between two points on a sphere. A simple Euclidean distance on degree coordinates would be wrong because 1° of longitude is ~111 km at the equator but ~0 km at the poles:

```
a = sin²(Δlat/2) + cos(lat₁) · cos(lat₂) · sin²(Δlon/2)
c = 2 · atan2(√a, √(1−a))
d = R · c       where R = 6 371 000 m
```

The total distance is the sum of Haversine distances between all consecutive GPS points.

**Speed from IMU via trapezoidal integration** — IMU accelerometers record acceleration (m/s²). To get velocity, you integrate over time. The **trapezoidal method** approximates the area under the acceleration curve as trapezoids rather than rectangles, which is more accurate:

```
v[i] = v[i−1] + (a[i−1] + a[i]) / 2 · Δt
```

Note: double-integrating IMU data to get position accumulates error over time (sensor drift). For accurate positioning, GPS correction is required. This implementation uses integration for velocity only, as a demonstration of the algorithm.

**Max acceleration** uses the **95th percentile** of the full IMU acceleration vector magnitude `√(AccX² + AccY² + AccZ²)` rather than the absolute maximum. This avoids single-sample noise spikes misrepresenting the actual peak acceleration.

**Altitude gain** is calculated as `max_altitude − start_altitude` (not `max − min`), which gives the actual climb from the takeoff point rather than being inflated by descent below the launch elevation.

**Sampling rate** is computed as `1 / mean(Δt)` where `Δt` is the difference between consecutive `TimeUS` values converted to seconds. Typical Ardupilot values: GPS 5–10 Hz, IMU 100–400 Hz. Both are displayed in the dashboard above the metrics panel.

---

### 3D Visualization

`visualization/plot3d.py` builds a Plotly 3D scatter/line chart using ENU coordinates:

- **Track line** — colored by speed (Viridis colorscale) or normalized time (Plasma colorscale)
- **Ground projection** — dotted gray line at Z=0 showing the 2D footprint of the flight
- **Start/finish markers** — green circle and red square with labels
- **Aspect mode** `data` — axes are scaled to real proportions so the trajectory isn't distorted

The chart is fully interactive: rotate with left-click drag, zoom with scroll, pan with right-click drag.

`visualization/map_view.py` builds a Folium map (Leaflet.js) with:
- Track split into per-segment polylines, each colored by speed (green → yellow → red gradient)
- Start/finish markers with popup showing coordinates, altitude and speed
- Waypoint dots every ~20 points with tooltips
- Layer switcher (OpenStreetMap, CartoDB light, CartoDB dark)
- Speed legend in the bottom-right corner

---

### AI Analysis

`ai/assistant.py` sends flight data to Google Gemini and returns a structured technical report.

**Anomaly detection** scans the GPS track before sending to the model:
- Sudden altitude drops > 5 m between consecutive points → flags with descent rate in m/s
- Sudden altitude gains > 5 m → flags with climb rate in m/s
- Ground speed > 20 m/s → flags as speed exceedance

Up to 10 anomalies are included in the prompt to avoid overloading the context.

**Prompt engineering** (`ai/prompts.py`): The prompt instructs Gemini to respond only in a strict structured format — no greetings, no filler text — with four sections: mission status, key metrics with assessments, detected anomalies, and a conclusion. `thinkingBudget: 0` disables the model's internal chain-of-thought reasoning, which otherwise consumed most of the output token budget before generating the actual answer.

**A/B comparison** (`analyze_flight_ab`): Calls `analyze_flight` for each selected model sequentially and returns a list of results. The UI renders them in side-by-side columns.

**Token tracking** (`ai/token_counter.py`): After each request, prompt and completion token counts from the API response are recorded in a module-level dict. The session totals are displayed in the AI tab as a token usage bar.

---

### Pipeline Logging

Every AI request is logged by `ai/pipeline_logger.py` with the following fields:

```json
{
  "timestamp": "2026-04-01T12:00:00Z",
  "filename": "00000001.BIN",
  "model": "gemini-2.5-flash",
  "prompt_tokens": 412,
  "completion_tokens": 387,
  "total_tokens": 799,
  "duration_s": 3.142,
  "metrics_snapshot": { ... },
  "prompt": "...",
  "response": "..."
}
```

**Local storage** (`LOG_STORAGE=local`): Logs are appended to a JSON file in `logs/ai_pipeline_YYYY-MM-DD.json`, one file per day. The `logs/` directory is git-ignored.

**MongoDB storage** (`LOG_STORAGE=mongodb`): Logs are inserted into the `ai_pipeline` collection in the configured database. If the MongoDB connection fails, the logger falls back to local JSON automatically.

---

## Stack & Rationale

| Library | Why this one |
|---|---|
| **pymavlink** | The only library that correctly decodes all DataFlash format versions. No alternative exists |
| **pandas** | Natural fit for tabular telemetry data — filtering, resampling, column ops |
| **numpy** | Vectorized math for coordinate transforms and metric calculations |
| **plotly** | Best Python library for interactive 3D charts without a JS build step |
| **folium** | Easiest way to get a Leaflet map in Python — no API key, fully offline tiles |
| **streamlit** | Fastest path from Python analysis code to a working web UI |
| **Gemini 2.5 Flash** | Free tier, fast, supports `thinkingBudget: 0` to disable CoT for structured outputs |
| **pymongo** | Thin driver, zero boilerplate, works well with the dict-based log structure |

---

## Docker Deployment

The `docker-compose.yml` spins up two services:

```yaml
app    — Streamlit on port 8501, mounts ./data and ./logs
mongo  — MongoDB 7 on port 27017, persistent volume mongo_data
```

```bash
# Build and start
cp .env.example .env
# Edit .env: set GEMINI_API_KEY and LOG_STORAGE=mongodb
docker-compose up --build

# Stop
docker-compose down

# Stop and remove data volume
docker-compose down -v
```

To run only the app without MongoDB:

```bash
docker build -t uav-analyzer .
docker run -p 8501:8501 --env-file .env uav-analyzer
```

---

## Tests

```bash
# Full scraper + metrics + ENU conversion smoke test
python tests/test_parser.py

# Raw pymavlink message type dump — useful for inspecting unknown .BIN files
python tests/test_mavlink.py
```

`test_parser.py` runs the full pipeline on `data/00000001.BIN` and prints all message types found, GPS point count, ENU coordinate ranges and all computed metrics. Use this to verify a new log file parses correctly before loading it in the UI.

`test_mavlink.py` prints every message type and its record count sorted by frequency. Useful for understanding what data a particular log file contains.
