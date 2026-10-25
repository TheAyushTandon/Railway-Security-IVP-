# Metro Safety AI — Edge Computer Vision Passenger Monitoring

A modular, local-first computer vision prototype for fixed metro station CCTV feeds running on an **RTX 5060 Laptop GPU** (8 GB GDDR7). Built for the **Image & Video Processing (IVP)** project.

---

## 👥 Engineering Division & Ownership

| Subsystem | Owner | Modules & Deliverables | Primary Contract |
|---|---|---|---|
| **Vision & Ingest** | **Person A** | • Video decode worker & 1 Hz randomized sampler<br/>• YOLO26n fine-tuning & evaluation<br/>• Next.js App Router UI & live dashboard | Emits `DetectionBatch` |
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
              • WebSocket Push: /api/v1/ws (Live state deltas)
                             │
                             ▼
               [ Next.js App Router UI ] (Person A)
```

---

## 📦 Core Data Contracts

1. **`DetectionBatch`** (`Person A` ➔ `Person B`): Raw vision input for a single frame. Contains normalized bboxes `[x1, y1, x2, y2] ∈ [0.0, 1.0]`, ISO 8601 UTC timestamps, and millisecond bucket offsets.
2. **`AnalyticsSnapshot`** (`Person B` ➔ `API/UI`): Aggregated operational summary containing active track count, instantaneous visible count, per-ROI counts, density class, and diagnostic latency (`sample_age_ms`).
3. **`AlertEvent`** (`Person B` ➔ `Storage/UI`): Actionable incidents with stable `event_id` (de-duplication ensures ongoing conditions update the existing incident instead of spamming alarms).

Sample JSON payloads and schemas are maintained in [`contracts/samples/`](contracts/samples) and [`contracts/events.schema.json`](contracts/events.schema.json).

---

## 🛠️ Getting Started

### 1. Backend Environment Setup
```powershell
# Navigate to project root
cd metro-safety-ai

# Activate virtual environment
.venv\Scripts\activate

# Install dependencies
pip install -e backend/
```

### 2. Run the Verification Test Suite
```powershell
pytest backend/app/tests -v
```

### 3. Run FastAPI Backend Dev Server
```powershell
cd backend
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```
* **API Documentation**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
* **Health Check**: [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health)
* **OpenAPI Schema**: [http://127.0.0.1:8000/contracts/openapi.json](http://127.0.0.1:8000/contracts/openapi.json)

---

## 📐 Milestone Gates

- [x] **Gate A (Week 1)**: Contracts merged, FastAPI skeleton ready, Person B tracking/counting/density/rules modules built, and 21 unit tests passing without GPU.
- [ ] **Gate B (Week 2)**: Offline video clip runs end-to-end through real YOLO detector, tracker, analytics, and generates snapshots.
- [ ] **Gate C (Week 3–4)**: Next.js dashboard connects via REST + WebSocket; 2+ cameras run with zero cross-talk.
- [ ] **Gate D (Week 5–6)**: Stress benchmark with 4 cameras; latency, count MAE, and limits documented.
