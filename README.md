# UAV Telemetry Analyzer

![Python](https://img.shields.io/badge/Python-3.11+-blue?style=flat-square&logo=python)
![Streamlit](https://img.shields.io/badge/Streamlit-1.56-red?style=flat-square&logo=streamlit)
![Gemini](https://img.shields.io/badge/Gemini-2.5_Flash-orange?style=flat-square&logo=google)
![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)

Web application for automated analysis of Ardupilot flight controller binary logs (.BIN) with 3D trajectory visualization, flight metric computation and AI-powered diagnostics.

## Stack

| Library | Purpose |
|---|---|
| **pymavlink** | Official Ardupilot library for parsing DataFlash binary format |
| **pandas / numpy** | Structured data frames and vectorized metric computation |
| **plotly** | Interactive 3D trajectory with colormap |
| **folium** | Leaflet.js map — no API key required |
| **streamlit** | Web UI without a frontend |
| **Google Gemini 2.5 Flash** | Free LLM for automated flight analysis |
| **requests** | HTTP client for Gemini API |
| **pymongo** | Optional AI pipeline log persistence in MongoDB |

## Quick Start

### Local

```bash
git clone https://github.com/Illia915/BEST-selection_project.git
cd BEST-selection_project
pip install -r requirements.txt
cp .env.example .env   # add your GEMINI_API_KEY
streamlit run app.py
```

Open `http://localhost:8501`

### Docker + MongoDB

```bash
cp .env.example .env
docker-compose up --build
```

Open `http://localhost:8501`

## Configuration

Copy `.env.example` → `.env`:

```env
GEMINI_API_KEY=AIza...           # get free key at aistudio.google.com
GEMINI_MODEL=gemini-2.5-flash    # default model
LOG_AI_PIPELINE=true             # log every AI request
LOG_STORAGE=local                # local (JSON) or mongodb
MONGO_URI=mongodb://localhost:27017
MONGO_DB=uav_telemetry
```

## Project Structure

```
.
├── app.py                      # Streamlit UI
├── Dockerfile
├── docker-compose.yml          # App + MongoDB
├── requirements.txt
├── .env.example
│
├── scraper/
│   └── dataflash.py            # Ardupilot .BIN parser (pymavlink)
│
├── analytics/
│   ├── metrics.py              # Haversine, trapezoidal integration, GPS filtering
│   └── coords.py               # WGS-84 → ECEF → ENU conversion
│
├── visualization/
│   ├── plot3d.py               # 3D trajectory (Plotly)
│   └── map_view.py             # 2D map (Folium / Leaflet)
│
├── ai/
│   ├── assistant.py            # Flight analysis, A/B model comparison
│   ├── prompts.py              # Gemini prompt templates
│   ├── token_counter.py        # Per-session token usage tracking
│   └── pipeline_logger.py      # JSON / MongoDB AI pipeline logging
│
├── data/
│   ├── 00000001.BIN
│   └── 00000019.BIN
│
├── logs/                       # AI pipeline JSON logs (git-ignored)
└── tests/
    ├── test_parser.py
    └── test_mavlink.py
```

## Features

### MVP
- Parse Ardupilot `.BIN` logs via pymavlink into pandas DataFrames
- GPS noise filtering (negative altitudes, coordinate outliers)
- Flight metrics:
  - Total distance via **Haversine formula**
  - Max horizontal / vertical speed
  - Max acceleration (95th percentile of IMU vector magnitude)
  - Altitude gain from takeoff point
  - Flight duration
  - Velocity from IMU via **trapezoidal integration**
- 3D trajectory with **WGS-84 → ECEF → ENU** conversion, colored by speed or time

### Nice-to-have
- Streamlit web dashboard with drag-and-drop file upload
- 2D Leaflet map (OpenStreetMap, no API key)
- **AI flight diagnostics** — Google Gemini 2.5 Flash produces a structured technical report with anomaly detection
- **A/B model comparison** — run multiple Gemini models simultaneously, compare outputs side-by-side
- **Token usage counter** — prompt + completion tokens shown per request and for the full session
- **AI pipeline logging** — every request stored with prompt, response, metrics snapshot and token counts (JSON or MongoDB)
- **Docker Compose** with MongoDB for persistent log storage

## Supported Gemini Models

| Model | Description |
|---|---|
| `gemini-2.5-flash` | Recommended — balanced speed and quality |
| `gemini-2.5-flash-lite` | Faster, lower cost |
| `gemini-2.5-pro` | Higher accuracy |

## Tests

```bash
python tests/test_parser.py
python tests/test_mavlink.py
```
