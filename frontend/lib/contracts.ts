/**
 * Metro Safety AI - TypeScript Contract Interfaces
 * Directly mirrors backend/app/vision/detection_schema.py and openapi.json.
 */

export interface Detection {
  class_name: string;
  confidence: number;
  bbox_norm: [number, number, number, number]; // [x1, y1, x2, y2] in [0, 1]
}

export interface DetectionBatch {
  schema_version: "1.0";
  camera_id: string;
  frame_id: string;
  captured_at: string;
  sample_bucket_start: string;
  sample_offset_ms: number;
  frame_width: number;
  frame_height: number;
  model_name: string;
  inference_ms: number;
  detections: Detection[];
}

export interface DensityInfo {
  class: "LOW" | "MEDIUM" | "HIGH";
  score: number;
  thresholds_version: string;
}

export interface AnalyticsSnapshot {
  schema_version: "1.0";
  camera_id: string;
  sampled_at: string;
  visible_detection_count: number;
  active_track_count: number;
  roi_counts: Record<string, number>;
  density: DensityInfo;
  inference_ms: number;
  pipeline_ms: number;
  sample_age_ms: number;
}

export interface AlertEvent {
  event_id: string;
  camera_id: string;
  type: "DENSITY_HIGH" | "PLATFORM_INTRUSION" | "WRONG_DIRECTION" | "LOITERING";
  severity: "info" | "warning" | "critical";
  status: "new" | "acknowledged" | "resolved";
  occurred_at: string;
  confidence: number;
  evidence: Record<string, any>;
  acknowledged_at?: string | null;
  resolved_at?: string | null;
}

export interface CameraRecord {
  camera_id: string;
  name: string;
  source_ref: string;
  status: "ANALYSIS_ACTIVE" | "STOPPED" | "DEGRADED" | "SOURCE_DEGRADED";
  last_sampled_at?: string | null;
  sample_age_ms?: number | null;
}

export interface SystemMetrics {
  timestamp: string;
  active_cameras_count: number;
  sample_rate_hz: number;
  dropped_samples_total: number;
  p50_latency_ms: number;
  p95_latency_ms: number;
  avg_inference_ms: number;
  avg_pipeline_ms: number;
  gpu_memory_used_mb: number;
}

export interface WebSocketEnvelope<T = any> {
  schema_version: "1.0";
  event_id: string;
  type:
    | "camera.status.changed"
    | "frame.sampled"
    | "analytics.snapshot.updated"
    | "alert.created"
    | "alert.acknowledged"
    | "pipeline.metrics.updated"
    | "heartbeat";
  occurred_at: string;
  camera_id: string;
  data: T;
}
