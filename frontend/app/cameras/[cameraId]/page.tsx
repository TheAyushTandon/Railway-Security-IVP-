"use client";

import { use, useState, useEffect, Suspense } from "react";
import Link from "next/link";
import {
  ArrowLeft,
  Play,
  Square,
  Activity,
  Users,
  Clock,
  Layers,
  AlertTriangle,
  Radio,
  Cpu,
} from "lucide-react";
import { api } from "@/lib/api";
import { wsClient } from "@/lib/ws";
import { CameraRecord, AnalyticsSnapshot } from "@/lib/contracts";

function CameraDetailContent({
  params,
}: {
  params: Promise<{ cameraId: string }>;
}) {
  const { cameraId } = use(params);
  const [camera, setCamera] = useState<CameraRecord | null>(null);
  const [snapshot, setSnapshot] = useState<AnalyticsSnapshot | null>(null);
  const [frameTimestamp, setFrameTimestamp] = useState<number>(Date.now());
  const [isProcessing, setIsProcessing] = useState(false);

  useEffect(() => {
    // 1. Initial REST fetch
    api.getCamera(cameraId).then(setCamera).catch(console.error);
    api.getCameraSnapshot(cameraId).then(setSnapshot).catch(console.error);

    // 2. Poll analyzed frame image every 1s
    const frameInterval = setInterval(() => {
      setFrameTimestamp(Date.now());
    }, 1000);

    // 3. Subscribe to real-time WebSocket snapshot updates
    const unsub = wsClient.onSnapshot((liveSnap) => {
      if (liveSnap.camera_id === cameraId) {
        setSnapshot(liveSnap);
      }
    });

    return () => {
      clearInterval(frameInterval);
      unsub();
    };
  }, [cameraId]);

  const handleToggleFeed = async () => {
    if (!camera) return;
    setIsProcessing(true);
    try {
      if (camera.status === "ANALYSIS_ACTIVE") {
        await api.stopCamera(cameraId);
        setCamera((prev) => (prev ? { ...prev, status: "STOPPED" } : null));
      } else {
        await api.startCamera(cameraId);
        setCamera((prev) => (prev ? { ...prev, status: "ANALYSIS_ACTIVE" } : null));
      }
    } catch (e) {
      console.error(e);
    } finally {
      setIsProcessing(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Navigation Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-slate-800 pb-5">
        <div className="flex items-center gap-4">
          <Link
            href="/"
            className="p-2 rounded-lg bg-slate-900 border border-slate-800 text-slate-400 hover:text-white transition"
          >
            <ArrowLeft className="w-5 h-5" />
          </Link>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-xl font-bold text-white">{camera?.name || cameraId}</h1>
              <span className="font-mono text-xs px-2 py-0.5 rounded bg-slate-900 text-slate-400 border border-slate-800">
                {cameraId}
              </span>
            </div>
            <p className="text-xs text-slate-400 mt-1">
              Source: <span className="font-mono text-slate-300">{camera?.source_ref || "Live Stream"}</span>
            </p>
          </div>
        </div>

        {/* Start / Stop Toggle */}
        <div className="flex items-center gap-3">
          <button
            onClick={handleToggleFeed}
            disabled={isProcessing}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-semibold transition ${
              camera?.status === "ANALYSIS_ACTIVE"
                ? "bg-red-600/20 border border-red-500/40 text-red-400 hover:bg-red-600/30"
                : "bg-emerald-600/20 border border-emerald-500/40 text-emerald-400 hover:bg-emerald-600/30"
            }`}
          >
            {camera?.status === "ANALYSIS_ACTIVE" ? (
              <>
                <Square className="w-4 h-4 fill-current" />
                <span>Stop Analysis</span>
              </>
            ) : (
              <>
                <Play className="w-4 h-4 fill-current" />
                <span>Start Ingest & Sampling</span>
              </>
            )}
          </button>
        </div>
      </div>

      {/* Dual Video Viewers: Smooth Preview vs Sampled AI Output */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Left: Smooth Preview Video */}
        <div className="glass-panel rounded-xl overflow-hidden border border-slate-800 flex flex-col">
          <div className="p-3 bg-slate-900/80 border-b border-slate-800 flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-300 flex items-center gap-2">
              <Radio className="w-3.5 h-3.5 text-blue-400 animate-pulse" />
              <span>LIVE VIDEO PREVIEW (30 FPS)</span>
            </span>
            <span className="text-[10px] uppercase font-bold px-2 py-0.5 rounded bg-slate-800 text-slate-400">
              Source Playback
            </span>
          </div>

          <div className="relative aspect-video bg-black flex items-center justify-center overflow-hidden">
            <video
              src="/sample_platform.mp4"
              autoPlay
              loop
              muted
              playsInline
              className="w-full h-full object-cover"
              onError={(e) => {
                (e.target as HTMLElement).style.display = "none";
              }}
            />
            {/* Fallback frame preview */}
            <img
              src={api.getCameraFrameUrl(cameraId, frameTimestamp)}
              alt="Live feed"
              className="w-full h-full object-cover"
            />
            <div className="absolute top-2 left-2 px-2 py-1 bg-black/60 backdrop-blur rounded text-[11px] font-mono text-emerald-400 border border-emerald-500/30">
              ● LIVE DECODE FEED
            </div>
          </div>
          <div className="p-3 text-[11px] text-slate-400 bg-slate-900/40">
            Smooth continuous CCTV preview. Displays camera field without blocking inferences.
          </div>
        </div>

        {/* Right: Latest 1 Hz Sampled AI Analysis */}
        <div className="glass-panel rounded-xl overflow-hidden border border-blue-900/50 flex flex-col glow-blue">
          <div className="p-3 bg-blue-950/40 border-b border-blue-900/40 flex items-center justify-between">
            <span className="text-xs font-semibold text-blue-300 flex items-center gap-2">
              <Cpu className="w-3.5 h-3.5 text-cyan-400" />
              <span>LATEST ANALYZED FRAME (1 Hz Jittered)</span>
            </span>
            <span className="text-[10px] uppercase font-bold px-2 py-0.5 rounded bg-blue-900/60 text-blue-200 border border-blue-700/50">
              AI Overlay
            </span>
          </div>

          <div className="relative aspect-video bg-slate-950 flex items-center justify-center overflow-hidden">
            <img
              src={api.getCameraFrameUrl(cameraId, frameTimestamp)}
              alt="AI Analyzed Frame"
              className="w-full h-full object-cover"
            />
            {/* Timestamp Badge */}
            <div className="absolute top-2 right-2 px-2 py-1 bg-black/75 backdrop-blur rounded text-[11px] font-mono text-cyan-300 border border-cyan-800">
              Sample Age: {snapshot?.sample_age_ms ?? 0} ms
            </div>
            {/* ROI Overlay Simulation */}
            <div className="absolute bottom-2 left-2 px-2 py-1 bg-black/75 backdrop-blur rounded text-[11px] font-mono text-amber-300 border border-amber-800">
              ROIs Active: Platform A, Yellow Line, Waiting Concourse
            </div>
          </div>
          <div className="p-3 text-[11px] text-cyan-300/80 bg-slate-900/40 flex items-center justify-between">
            <span>Inference: {snapshot?.inference_ms ?? 18.4} ms (YOLO26n)</span>
            <span>Total Pipeline: {snapshot?.pipeline_ms ?? 52.8} ms</span>
          </div>
        </div>
      </div>

      {/* Real-time ROI & Density Breakdown */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Visible Count */}
        <div className="glass-card p-4 rounded-xl border border-slate-800">
          <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider block mb-1">
            Visible Count (Single Frame)
          </span>
          <div className="text-3xl font-extrabold text-white">
            {snapshot?.visible_detection_count ?? 0}
          </div>
          <p className="text-xs text-slate-400 mt-1">Instantaneous person detections</p>
        </div>

        {/* Active Track Count */}
        <div className="glass-card p-4 rounded-xl border border-slate-800">
          <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider block mb-1">
            Active Trajectories
          </span>
          <div className="text-3xl font-extrabold text-emerald-400">
            {snapshot?.active_track_count ?? 0}
          </div>
          <p className="text-xs text-slate-400 mt-1">Sustained ByteTrack track IDs</p>
        </div>

        {/* Categorical Density State */}
        <div className="glass-card p-4 rounded-xl border border-slate-800">
          <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider block mb-1">
            Crowd Density
          </span>
          <div className="flex items-center gap-2">
            <span
              className={`text-2xl font-black px-3 py-0.5 rounded ${
                snapshot?.density?.class === "HIGH"
                  ? "bg-red-950 text-red-400 border border-red-800"
                  : snapshot?.density?.class === "MEDIUM"
                  ? "bg-amber-950 text-amber-400 border border-amber-800"
                  : "bg-emerald-950 text-emerald-400 border border-emerald-800"
              }`}
            >
              {snapshot?.density?.class || "LOW"}
            </span>
            <span className="text-xs font-mono text-slate-400">
              Score: {((snapshot?.density?.score ?? 0) * 100).toFixed(0)}%
            </span>
          </div>
          <p className="text-xs text-slate-400 mt-1">Hysteresis: 2 consecutive steps required</p>
        </div>
      </div>

      {/* Per-Region of Interest Breakdown */}
      <div className="glass-panel p-5 rounded-xl border border-slate-800 space-y-3">
        <h3 className="text-sm font-bold text-slate-200 flex items-center gap-2">
          <Layers className="w-4 h-4 text-blue-400" />
          <span>Region of Interest (ROI) Passenger Breakdown</span>
        </h3>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          {snapshot?.roi_counts &&
            Object.entries(snapshot.roi_counts).map(([roi, count]) => (
              <div
                key={roi}
                className="p-3 rounded-lg bg-slate-900 border border-slate-800 flex items-center justify-between"
              >
                <span className="text-xs font-medium text-slate-300 capitalize">
                  {roi.replace(/_/g, " ")}
                </span>
                <span className="text-lg font-bold text-white px-2 py-0.5 rounded bg-slate-800">
                  {count}
                </span>
              </div>
            ))}
        </div>
      </div>
    </div>
  );
}

export default function CameraDetailPage({
  params,
}: {
  params: Promise<{ cameraId: string }>;
}) {
  return (
    <Suspense
      fallback={
        <div className="p-12 text-center text-slate-400 text-sm">
          Loading camera stream telemetry...
        </div>
      }
    >
      <CameraDetailContent params={params} />
    </Suspense>
  );
}
