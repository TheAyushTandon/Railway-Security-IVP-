"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState, useEffect, Suspense } from "react";
import { ShieldAlert, Video, Bell, Activity, Cpu, Radio } from "lucide-react";
import { wsClient } from "@/lib/ws";

function NavbarInner() {
  const pathname = usePathname();
  const [wsConnected, setWsConnected] = useState(false);

  useEffect(() => {
    wsClient.connect();
    const unsub = wsClient.onConnectionChange((connected) => {
      setWsConnected(connected);
    });
    return () => {
      unsub();
    };
  }, []);

  const navItems = [
    { name: "Overview", href: "/", icon: Activity },
    { name: "Cameras", href: "/cameras/cam_01", icon: Video },
    { name: "Alerts Center", href: "/alerts", icon: Bell },
    { name: "Diagnostics", href: "/diagnostics", icon: Cpu },
  ];

  return (
    <header className="sticky top-0 z-50 glass-panel border-b border-slate-800">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Brand */}
          <div className="flex items-center gap-3">
            <div className="p-2 bg-blue-600/20 border border-blue-500/40 rounded-lg text-blue-400">
              <ShieldAlert className="w-6 h-6" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="font-bold text-lg tracking-wider text-slate-100">METRO SAFETY AI</span>
                <span className="text-[10px] uppercase font-semibold px-2 py-0.5 rounded bg-blue-950 text-blue-300 border border-blue-800">
                  Blackwell RTX 5060
                </span>
              </div>
              <p className="text-xs text-slate-400">Autonomous Edge Passenger Safety & Crowd Analytics</p>
            </div>
          </div>

          {/* Navigation Links */}
          <nav className="flex items-center gap-1">
            {navItems.map((item) => {
              const Icon = item.icon;
              const isActive = pathname === item.href;
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={`flex items-center gap-2 px-3 py-2 rounded-md text-sm font-medium transition-all ${
                    isActive
                      ? "bg-blue-600/20 text-blue-400 border border-blue-500/30"
                      : "text-slate-400 hover:text-slate-200 hover:bg-slate-800/60"
                  }`}
                >
                  <Icon className="w-4 h-4" />
                  <span>{item.name}</span>
                </Link>
              );
            })}
          </nav>

          {/* Live WS Connection Pill */}
          <div className="flex items-center gap-3">
            <div
              className={`flex items-center gap-2 px-3 py-1 rounded-full text-xs font-medium border ${
                wsConnected
                  ? "bg-emerald-950/70 border-emerald-700/50 text-emerald-400"
                  : "bg-amber-950/70 border-amber-700/50 text-amber-400"
              }`}
            >
              <Radio className={`w-3.5 h-3.5 ${wsConnected ? "animate-pulse" : ""}`} />
              <span>{wsConnected ? "LIVE WS ACTIVE" : "RECONNECTING"}</span>
            </div>
          </div>
        </div>
      </div>
    </header>
  );
}

export default function Navbar() {
  return (
    <Suspense
      fallback={
        <header className="sticky top-0 z-50 glass-panel border-b border-slate-800">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-blue-600/20 border border-blue-500/40 rounded-lg text-blue-400">
                <ShieldAlert className="w-6 h-6" />
              </div>
              <span className="font-bold text-lg text-slate-100">METRO SAFETY AI</span>
            </div>
          </div>
        </header>
      }
    >
      <NavbarInner />
    </Suspense>
  );
}
