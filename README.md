# Metro Safety AI — Edge Computer Vision Passenger Monitoring

A modular, local-first computer vision prototype for fixed metro station CCTV feeds running on an **RTX 5060 Laptop GPU** (8 GB GDDR7). Built for the **Image & Video Processing (IVP)** project.

---

## 👥 Engineering Division & Ownership

| Subsystem | Owner | Modules & Deliverables | Primary Contract |
|---|---|---|---|
| **Vision & Ingest** | **Person A** | • Video decode worker & 1 Hz randomized sampler<br/>• YOLO26n/YOLO11n fine-tuning & evaluation<br/>• Next.js App Router UI & live dashboard | Emits `DetectionBatch` |
| **Analytics & Backend** | **Person B** | • ByteTrack tracker adapter & camera track state<br/>• ROI & line-crossing counts<br/>• Crowd density evaluation with hysteresis<br/>• Anomaly rules engine with alert de-duplication<br/>• FastAPI REST & WebSocket endpoints<br/>• SQLite storage & persistence | Consumes `DetectionBatch`<br/>Emits `AnalyticsSnapshot` & `AlertEvent` |
| **Shared** | **Both** | • Core API schemas & OpenAPI contract<br/>• FastAPI monolith lifecycle & worker isolation<br/>• Multi-camera benchmark harness | Contracts in `contracts/` |

---

## 🏛️ Pipeline Architecture

```
[ Camera Stream / Video Feed ]
              │
              ▼ (Person A)
   [ 1 Hz Random Sampler ]  ──► Selects 1 frame/sec (jitter offset 200–800 ms)
              │
              ▼ (Person A)
     [ YOLO26n Detector ]   ──► Single GPU worker; emits normalized bboxes
              │
              ▼  (Contract: DetectionBatch)
   [ ByteTrack & Tracker ]  ──► (Person B) Scoped to camera; calculates movement trends
              │
              ▼  (Person B)
  [ Counting, Density & Rules ]
  • ROI headcounts (platform, stairs, hazard zones)
  • Crowd density (LOW / MEDIUM / HIGH with hysteresis)
  • Platform intrusion, loitering, wrong direction
              │
              ├────────────────────────────┐
              ▼                            ▼
  (AnalyticsSnapshot)                (AlertEvent)
  • Visible & active counts          • De-duplicated incident UUIDs
  • Per-ROI breakdown                • Operator ack audit log
  • Latency & sample age             • Stored in SQLite
              │                            │
              └──────────────┬─────────────┘
                             ▼
              [ FastAPI Modular Monolith ]
              • REST Endpoints: /api/v1/cameras, /events, /metrics
              • WebSocket Push: /ws/live (Live state deltas)
                             │
                             ▼
               [ Next.js App Router UI ] (Person A / Option A)
```

---

## 📦 Core Data Contracts

1. **`DetectionBatch`** (`Person A` ➔ `Person B`): Raw vision input for a single frame. Contains normalized bboxes `[x1, y1, x2, y2] ∈ [0.0, 1.0]`, ISO 8601 UTC timestamps, and millisecond bucket offsets.
2. **`AnalyticsSnapshot`** (`Person B` ➔ `API/UI`): Aggregated operational summary containing active track count, instantaneous visible count, per-ROI counts, density class, and diagnostic latency (`sample_age_ms`).
3. **`AlertEvent`** (`Person B` ➔ `Storage/UI`): Actionable incidents with stable `event_id` (de-duplication ensures ongoing conditions update the existing incident instead of spamming alarms).

Sample JSON payloads and schemas are maintained in [`contracts/samples/`](contracts/samples) and [`contracts/events.schema.json`](contracts/events.schema.json).

---

## 🚀 Running the Project

### 1. Backend Environment Setup & Verification
```powershell
# Navigate to project root
cd "d:\PROJECTS\image and video processing project\metro-safety-ai"

# Run the 28-test verification suite
.venv\Scripts\python.exe -m pytest backend/app/tests -v
```

### 2. Launch FastAPI Backend Server
```powershell
cd backend
..\.venv\Scripts\uvicorn.exe app.main:app --reload --host 127.0.0.1 --port 8000
```
* **API Documentation**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
* **Live WebSocket**: `ws://127.0.0.1:8000/ws/live`
* **Health Check**: [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health)

### 3. Launch Next.js Operator Dashboard (Option A)
```powershell
cd frontend
npm run dev
```
* **Web UI URL**: [http://localhost:3000](http://localhost:3000)
* Features:
  - **Overview Dashboard**: Fleet cards, visible & track totals, density gauges, real-time alerts feed.
  - **Camera Detail View**: Dual viewer comparing 30 FPS smooth decode preview vs 1 Hz AI analyzed frame overlay.
  - **Alerts Center**: Filterable incidents with operator acknowledgement audit log.
  - **Diagnostics & Benchmarks**: Latency histogram and PRD guardrail compliance checklist.

### 4. Dataset & Model Training Pipeline (Option B)
```powershell
# Step 1: Prepare MetroStation dataset (or bootstrap platform baseline)
.venv\Scripts\python.exe scripts/prepare_dataset.py

# Step 2: Train YOLO detector (deterministic seed 42, auto OOM batch drop)
.venv\Scripts\python.exe scripts/train_yolo.py --epochs 30 --batch 8

# Step 3: Evaluate model & generate benchmark report
.venv\Scripts\python.exe scripts/evaluate_model.py
```
* Output Report: [`docs/EVALUATION_REPORT.md`](docs/EVALUATION_REPORT.md)
* Architecture Spec: [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)
* Hardware Edge Limits: [`docs/LIMITATIONS.md`](docs/LIMITATIONS.md)

---

## 📐 Milestone Gates

- [x] **Gate A (Week 1)**: Contracts merged, FastAPI skeleton ready, Person B tracking/counting/density/rules modules built, and 28 unit/integration tests passing.
- [x] **Gate B (Week 2)**: Offline video clip runs end-to-end through detector, tracker, analytics, and generates snapshots.
- [x] **Gate C (Week 3–4)**: Next.js dashboard connects via REST + WebSocket; live feeds display dual preview/analyzed views with zero cross-talk.
- [ ] **Gate D (Week 5–6)**: Stress benchmark with 4 cameras; latency, count MAE, and thermal power limits documented.
