/**
 * Dashboard — landing page after login.
 */

import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  Plus,
  ShieldCheck,
  Activity,
  Boxes,
  ArrowRight,
  Zap,
} from "lucide-react";
import { canvasApi } from "../lib/api";
import type { Canvas } from "../lib/types";

export function Dashboard() {
  const [canvases, setCanvases] = useState<Canvas[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    canvasApi
      .list()
      .then(setCanvases)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  async function createCanvas() {
    try {
      const canvas = await canvasApi.create({
        title: `Architecture ${new Date().toLocaleDateString()}`,
      });
      window.location.href = `/canvas/${canvas.id}`;
    } catch (e) {
      console.error("Failed to create canvas:", e);
    }
  }

  return (
    <div className="min-h-screen bg-zinc-950 text-zinc-200">
      {/* Header */}
      <header className="border-b border-zinc-800/50 bg-zinc-950/80 backdrop-blur-sm sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <ShieldCheck className="w-6 h-6 text-blue-400" />
            <span className="text-lg font-semibold tracking-tight">
              ZTForge
            </span>
            <span className="text-[10px] bg-blue-500/10 text-blue-400 px-2 py-0.5 rounded-full font-medium">
              MVP
            </span>
          </div>
          <nav className="flex items-center gap-6">
            <Link
              to="/hub"
              className="text-sm text-zinc-500 hover:text-zinc-300 transition-colors"
            >
              Policy Hub
            </Link>
            <button
              onClick={createCanvas}
              className="flex items-center gap-2 bg-blue-600 hover:bg-blue-500 text-white rounded-lg px-4 py-2 text-sm font-medium transition-colors"
            >
              <Plus className="w-4 h-4" />
              New Canvas
            </button>
          </nav>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-6 py-10">
        {/* Hero section — not a generic card grid */}
        <div className="grid grid-cols-1 lg:grid-cols-5 gap-8 mb-12">
          <div className="lg:col-span-3">
            <h1 className="text-3xl font-bold tracking-tight text-zinc-100 mb-3">
              Zero Trust Architecture
            </h1>
            <p className="text-zinc-500 text-base leading-relaxed max-w-xl">
              Design, simulate, and enforce Zero Trust policies visually.
              Drag nodes onto the canvas, connect them with policy-governed
              edges, and run breach simulations to validate your architecture.
            </p>
            <div className="flex items-center gap-4 mt-6">
              <div className="flex items-center gap-2 text-sm text-zinc-500">
                <Boxes className="w-4 h-4 text-emerald-400" />
                <span>{canvases.length} canvases</span>
              </div>
              <div className="flex items-center gap-2 text-sm text-zinc-500">
                <Activity className="w-4 h-4 text-amber-400" />
                <span>Posture monitoring</span>
              </div>
            </div>
          </div>

          {/* Quick actions */}
          <div className="lg:col-span-2 flex flex-col gap-3">
            <button
              onClick={createCanvas}
              className="flex items-center justify-between bg-zinc-900 border border-zinc-800 rounded-xl p-4 hover:border-zinc-700 transition-colors group"
            >
              <div className="flex items-center gap-3">
                <div className="p-2 bg-blue-500/10 rounded-lg">
                  <Plus className="w-5 h-5 text-blue-400" />
                </div>
                <div className="text-left">
                  <div className="text-sm font-medium text-zinc-200">
                    New Architecture
                  </div>
                  <div className="text-xs text-zinc-600">
                    Start from scratch
                  </div>
                </div>
              </div>
              <ArrowRight className="w-4 h-4 text-zinc-600 group-hover:text-zinc-400 transition-colors" />
            </button>

            <Link
              to="/hub"
              className="flex items-center justify-between bg-zinc-900 border border-zinc-800 rounded-xl p-4 hover:border-zinc-700 transition-colors group"
            >
              <div className="flex items-center gap-3">
                <div className="p-2 bg-purple-500/10 rounded-lg">
                  <Zap className="w-5 h-5 text-purple-400" />
                </div>
                <div className="text-left">
                  <div className="text-sm font-medium text-zinc-200">
                    Browse Templates
                  </div>
                  <div className="text-xs text-zinc-600">
                    Fork community policies
                  </div>
                </div>
              </div>
              <ArrowRight className="w-4 h-4 text-zinc-600 group-hover:text-zinc-400 transition-colors" />
            </Link>
          </div>
        </div>

        {/* Canvas list */}
        <div className="mb-6">
          <h2 className="text-lg font-semibold text-zinc-300 mb-4">
            Your Canvases
          </h2>

          {loading && (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {[1, 2, 3].map((i) => (
                <div key={i} className="bg-zinc-900 rounded-xl p-5 animate-pulse">
                  <div className="h-5 w-2/3 bg-zinc-800 rounded mb-3" />
                  <div className="h-3 w-full bg-zinc-800/50 rounded mb-2" />
                  <div className="h-3 w-1/2 bg-zinc-800/50 rounded" />
                </div>
              ))}
            </div>
          )}

          {!loading && canvases.length === 0 && (
            <div className="flex flex-col items-center py-16 text-center">
              <Boxes className="w-12 h-12 text-zinc-800 mb-4" />
              <p className="text-sm text-zinc-500 mb-1">No canvases yet</p>
              <p className="text-xs text-zinc-600 mb-4">
                Create your first Zero Trust architecture
              </p>
              <button
                onClick={createCanvas}
                className="text-sm text-blue-400 hover:text-blue-300 transition-colors"
              >
                Create canvas →
              </button>
            </div>
          )}

          {!loading && canvases.length > 0 && (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {canvases.map((c) => (
                <Link
                  key={c.id}
                  to={`/canvas/${c.id}`}
                  className="bg-zinc-900 border border-zinc-800 rounded-xl p-5 hover:border-zinc-700 transition-all hover:shadow-lg group"
                >
                  <h3 className="text-sm font-medium text-zinc-200 group-hover:text-white transition-colors">
                    {c.title}
                  </h3>
                  {c.description && (
                    <p className="text-xs text-zinc-600 mt-1 line-clamp-2">
                      {c.description}
                    </p>
                  )}
                  <div className="flex items-center gap-3 mt-3">
                    <span className="text-[10px] text-zinc-600">
                      v{c.version}
                    </span>
                    <span className="text-[10px] text-zinc-600">
                      {new Date(c.updated_at).toLocaleDateString()}
                    </span>
                    <span className={`text-[10px] px-1.5 py-0.5 rounded ${
                      c.visibility === "public"
                        ? "bg-emerald-500/10 text-emerald-500"
                        : "bg-zinc-800 text-zinc-600"
                    }`}>
                      {c.visibility}
                    </span>
                  </div>
                </Link>
              ))}
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
