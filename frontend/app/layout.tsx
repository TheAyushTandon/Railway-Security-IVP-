import type { Metadata } from "next";
import "./globals.css";
import Navbar from "@/components/Navbar";

export const metadata: Metadata = {
  title: "Metro Safety AI — Edge Computer Vision Monitoring",
  description: "Real-time passenger safety, crowd occupancy, and anomaly detection dashboard.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body className="bg-slate-950 text-slate-100 min-h-screen flex flex-col font-sans">
        <Navbar />
        <main className="flex-1 max-w-7xl w-full mx-auto p-4 sm:p-6 lg:p-8">
          {children}
        </main>
        <footer className="border-t border-slate-900 py-4 text-center text-xs text-slate-500">
          Metro Safety AI Prototype — Modular Monolith Architecture | 1 Hz Randomized Sampling Policy
        </footer>
      </body>
    </html>
  );
}
