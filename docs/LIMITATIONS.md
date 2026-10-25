# Metro Safety AI — Edge Prototype Limitations & Guardrails

## 1. Algorithmic Limitations

### 1.1 Sparse (1 Hz) Randomized Sampling vs Fast Motion
- **Symptom:** Because inference is executed once per second with a randomized offset ($[0.20, 0.80]$s), a passenger running rapidly across a narrow platform boundary might cross the tripwire in $<0.6$s and avoid detection during that specific transition window.
- **Mitigation:** The live CCTV stream remains visible at 30 FPS for human operators; tripwire zones and platform intrusion ROIs are calibrated with spatial buffer margins (e.g. 0.5m setback).

### 1.2 ByteTrack Re-Identification Across Extended Gaps
- **Symptom:** Standard ByteTrack relies primarily on bounding box spatial continuity (IoU) and Kalman velocity state. If a passenger stops or moves significantly during the 1-second gap between frames, an ID switch may occur.
- **Mitigation:** The tracker integrates dynamic timestamp deltas ($\Delta t = t_k - t_{k-1}$) rather than static 30 FPS time constants, and maintains an expiry TTL of 3.0 seconds to prevent premature track purges.

### 1.3 Occlusion & Platform Reflections
- **Symptom:** Wet polished granite or stainless steel platform surfaces can produce inverted specular reflections of passengers, potentially triggering false person detections if confidence thresholds are set below 0.35.
- **Mitigation:** Operating confidence threshold is enforced at $\ge 0.40$ in `DetectorService`, and bounding box aspect ratios are validated.

---

## 2. Hardware & Thermal Limitations (RTX 5060 Laptop GPU)

### 2.1 Thermal Throttling & Power Limits
- The mobile RTX 5060 has a maximum dynamic boost TGP of 70W. Under sustained maximum workload (simultaneous training and decoding 4+ feeds), clock speeds drop from ~2400 MHz to ~1800 MHz.
- **Rule:** Training jobs must not be executed concurrently with real-time live multi-camera inference.

### 2.2 VRAM Overhead
- With 8,151 MiB GDDR7 VRAM, desktop compositing (Windows DWM), browser hardware acceleration, and the IDE consume ~2.1 GB of VRAM at baseline.
- **Rule:** Model training starts with `batch=8` and automatically drops to `batch=4` or `batch=2` if an Out-Of-Memory (OOM) exception is caught.

---

## 3. Prototype Scope vs Commercial Production

| Dimension | Edge Prototype (Current) | Commercial Production Deployment |
|-----------|--------------------------|----------------------------------|
| **Database** | SQLite with WAL mode & indexes | PostgreSQL with TimescaleDB / partitioning |
| **Video Transport** | Direct OpenCV MP4/RTSP decode | MediaMTX / WebRTC low-latency streaming proxy |
| **Model Serving** | Single in-process PyTorch model worker | TensorRT engine via Triton Inference Server |
| **Authentication** | Local operator token | Enterprise OAuth2 / OIDC with RBAC |
| **Multi-Node** | Single edge station computer | Distributed Kubernetes cluster across 20+ stations |
