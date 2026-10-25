"use client";

import { useState, useEffect } from "react";
import {
  Bell,
  AlertTriangle,
  CheckCircle,
  Filter,
  RefreshCw,
  ShieldAlert,
} from "lucide-react";
import { api } from "@/lib/api";
import { wsClient } from "@/lib/ws";
import { AlertEvent } from "@/lib/contracts";

export default function AlertsCenterPage() {
  const [alerts, setAlerts] = useState<AlertEvent[]>([]);
  const [severityFilter, setSeverityFilter] = useState<string>("all");
  const [loading, setLoading] = useState(true);

  const fetchAlerts = async () => {
    setLoading(true);
    try {
      const data = await api.getEvents({
        severity: severityFilter === "all" ? undefined : severityFilter,
        limit: 50,
      });
      setAlerts(data);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAlerts();

    const unsub = wsClient.onAlert((newAlert) => {
      setAlerts((prev) => {
        const existingIdx = prev.findIndex((a) => a.event_id === newAlert.event_id);
        if (existingIdx >= 0) {
          const updated = [...prev];
          updated[existingIdx] = newAlert;
          return updated;
        }
        return [newAlert, ...prev];
      });
    });

    return () => unsub();
  }, [severityFilter]);

  const handleAck = async (eventId: string) => {
    try {
      const updated = await api.acknowledgeEvent(eventId, "station_supervisor");
      setAlerts((prev) =>
        prev.map((a) => (a.event_id === eventId ? updated : a))
      );
    } catch (e) {
      console.error(e);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-slate-800 pb-5">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-3">
            <Bell className="w-6 h-6 text-amber-400" />
            <span>Safety Alerts & Incidents Center</span>
          </h1>
          <p className="text-sm text-slate-400 mt-1">
            Real-time audit log of platform intrusions, crowd spikes, loitering, and movement violations.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={fetchAlerts}
            className="flex items-center gap-2 px-3 py-2 rounded-lg bg-slate-900 border border-slate-800 text-xs font-semibold text-slate-300 hover:text-white transition"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
            <span>Refresh</span>
          </button>
        </div>
      </div>

      {/* Filter Tabs */}
      <div className="flex items-center gap-2 border-b border-slate-800 pb-3">
        <Filter className="w-4 h-4 text-slate-500 mr-2" />
        {["all", "critical", "warning", "info"].map((sev) => (
          <button
            key={sev}
            onClick={() => setSeverityFilter(sev)}
            className={`px-3 py-1.5 rounded-md text-xs font-semibold capitalize transition ${
              severityFilter === sev
                ? "bg-blue-600 text-white"
                : "bg-slate-900 text-slate-400 hover:text-slate-200"
            }`}
          >
            {sev}
          </button>
        ))}
      </div>

      {/* Alerts Table */}
      <div className="glass-panel rounded-xl border border-slate-800 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm text-slate-300">
            <thead className="bg-slate-900/80 text-xs font-semibold uppercase text-slate-400 border-b border-slate-800">
              <tr>
                <th className="px-4 py-3">Severity</th>
                <th className="px-4 py-3">Anomaly Type</th>
                <th className="px-4 py-3">Camera</th>
                <th className="px-4 py-3">Evidence / Dwell</th>
                <th className="px-4 py-3">Time</th>
                <th className="px-4 py-3">Status</th>
                <th className="px-4 py-3 text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 font-sans">
              {alerts.length === 0 ? (
                <tr>
                  <td colSpan={7} className="px-4 py-12 text-center text-slate-500 text-xs">
                    No alert incidents match the current filter.
                  </td>
                </tr>
              ) : (
                alerts.map((alert) => (
                  <tr key={alert.event_id} className="hover:bg-slate-800/30 transition">
                    {/* Severity */}
                    <td className="px-4 py-3 whitespace-nowrap">
                      <span
                        className={`text-[10px] font-black uppercase px-2 py-0.5 rounded ${
                          alert.severity === "critical"
                            ? "bg-red-950 text-red-400 border border-red-800"
                            : alert.severity === "warning"
                            ? "bg-amber-950 text-amber-400 border border-amber-800"
                            : "bg-blue-950 text-blue-400 border border-blue-800"
                        }`}
                      >
                        {alert.severity}
                      </span>
                    </td>

                    {/* Type */}
                    <td className="px-4 py-3 font-semibold text-white whitespace-nowrap">
                      {alert.type.replace(/_/g, " ")}
                    </td>

                    {/* Camera */}
                    <td className="px-4 py-3 font-mono text-xs text-slate-300 whitespace-nowrap">
                      {alert.camera_id}
                    </td>

                    {/* Evidence */}
                    <td className="px-4 py-3 text-xs text-slate-400">
                      {alert.evidence?.roi_id && (
                        <span className="font-medium text-slate-300">
                          Zone: {alert.evidence.roi_id}
                        </span>
                      )}
                      {alert.evidence?.dwell_duration_sec && (
                        <span className="ml-2 font-mono text-[11px] text-amber-400">
                          ({alert.evidence.dwell_duration_sec}s dwell)
                        </span>
                      )}
                      {alert.evidence?.density_score && (
                        <span className="ml-2 font-mono text-[11px] text-amber-400">
                          (Score: {(alert.evidence.density_score * 100).toFixed(0)}%)
                        </span>
                      )}
                    </td>

                    {/* Time */}
                    <td className="px-4 py-3 text-xs text-slate-400 whitespace-nowrap font-mono">
                      {new Date(alert.occurred_at).toLocaleTimeString()}
                    </td>

                    {/* Status */}
                    <td className="px-4 py-3 whitespace-nowrap">
                      {alert.status === "acknowledged" ? (
                        <span className="text-xs text-emerald-400 font-semibold flex items-center gap-1">
                          <CheckCircle className="w-3.5 h-3.5" /> Acknowledged
                        </span>
                      ) : (
                        <span className="text-xs text-amber-400 font-semibold flex items-center gap-1">
                          <AlertTriangle className="w-3.5 h-3.5" /> New
                        </span>
                      )}
                    </td>

                    {/* Action */}
                    <td className="px-4 py-3 text-right whitespace-nowrap">
                      {alert.status !== "acknowledged" ? (
                        <button
                          onClick={() => handleAck(alert.event_id)}
                          className="px-3 py-1 bg-blue-600 hover:bg-blue-500 text-white rounded text-xs font-semibold transition"
                        >
                          Acknowledge
                        </button>
                      ) : (
                        <span className="text-[11px] text-slate-500 font-mono">
                          {alert.evidence?.acknowledged_by || "Verified"}
                        </span>
                      )}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
