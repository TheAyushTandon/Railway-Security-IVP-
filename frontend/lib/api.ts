import { CameraRecord, AnalyticsSnapshot, AlertEvent, SystemMetrics } from "./contracts";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || "http://127.0.0.1:8000";

async function fetchJson<T>(path: string, options?: RequestInit): Promise<T> {
  const url = `${API_BASE}${path}`;
  const res = await fetch(url, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(options?.headers || {}),
    },
    cache: "no-store",
  });

  if (!res.ok) {
    let errorDetail = `HTTP ${res.status}: ${res.statusText}`;
    try {
      const errorJson = await res.json();
      if (errorJson.detail) errorDetail = errorJson.detail;
    } catch {
      // ignore
    }
    throw new Error(errorDetail);
  }

  return res.json();
}

export const api = {
  getHealth: () => fetchJson<{ status: string; model_loaded: boolean; gpu_name: string; version: string }>("/health"),

  getCameras: () => fetchJson<CameraRecord[]>("/api/v1/cameras"),

  getCamera: (cameraId: string) => fetchJson<CameraRecord>(`/api/v1/cameras/${cameraId}`),

  startCamera: (cameraId: string) =>
    fetchJson<{ message: string; status: string }>(`/api/v1/cameras/${cameraId}/start`, { method: "POST" }),

  stopCamera: (cameraId: string) =>
    fetchJson<{ message: string; status: string }>(`/api/v1/cameras/${cameraId}/stop`, { method: "POST" }),

  getCameraSnapshot: (cameraId: string) =>
    fetchJson<AnalyticsSnapshot>(`/api/v1/cameras/${cameraId}/snapshot`),

  getCameraFrameUrl: (cameraId: string, cacheBust?: number) =>
    `${API_BASE}/api/v1/cameras/${cameraId}/frame.jpg${cacheBust ? `?t=${cacheBust}` : ""}`,

  getEvents: (params?: { camera_id?: string; type?: string; severity?: string; limit?: number }) => {
    const searchParams = new URLSearchParams();
    if (params?.camera_id) searchParams.set("camera_id", params.camera_id);
    if (params?.type) searchParams.set("type", params.type);
    if (params?.severity) searchParams.set("severity", params.severity);
    if (params?.limit) searchParams.set("limit", params.limit.toString());
    const query = searchParams.toString();
    return fetchJson<AlertEvent[]>(`/api/v1/events${query ? `?${query}` : ""}`);
  },

  acknowledgeEvent: (eventId: string, actorId: string = "station_operator") =>
    fetchJson<AlertEvent>(`/api/v1/events/${eventId}/ack`, {
      method: "POST",
      body: JSON.stringify({ actor_id: actorId }),
    }),

  getMetrics: () => fetchJson<SystemMetrics>("/api/v1/metrics"),
};
