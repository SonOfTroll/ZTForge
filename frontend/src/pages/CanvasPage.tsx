/**
 * CanvasPage — full-screen canvas workspace with side panels.
 */

import { useState } from "react";
import { useParams, Link } from "react-router-dom";
import { ArrowLeft, Zap, Download, ShieldCheck } from "lucide-react";
import { Canvas } from "../components/Canvas";
import { SimulatorPanel } from "../components/SimulatorPanel";
import { hubApi } from "../lib/api";
import type { SimulationResult } from "../lib/types";

export function CanvasPage() {
  const { id } = useParams<{ id: string }>();
  const [showSimulator, setShowSimulator] = useState(false);
  const [showExport, setShowExport] = useState(false);
  // TODO(collab): get from auth context once Keycloak is integrated
  const userId = "demo-user";
  const displayName = "Demo User";

  if (!id) {
    return (
      <div className="h-screen flex items-center justify-center bg-zinc-950 text-zinc-500">
        No canvas ID provided
      </div>
    );
  }

  async function handleExport(format: string) {
    try {
      const content = await hubApi.export(id!, format);
      const blob = new Blob([content], { type: "text/plain" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `ztforge-${format}.${format === "pomerium" ? "yaml" : format === "iptables" ? "sh" : format === "terraform" ? "tf" : "rego"}`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (e) {
      console.error("Export failed:", e);
    }
  }

  return (
    <div className="h-screen flex flex-col bg-zinc-950">
      {/* Minimal top bar */}
      <div className="flex items-center justify-between px-4 py-2 border-b border-zinc-800/50 bg-zinc-950/90 backdrop-blur-sm z-20">
        <Link
          to="/"
          className="flex items-center gap-2 text-zinc-500 hover:text-zinc-300 transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          <ShieldCheck className="w-4 h-4 text-blue-400" />
          <span className="text-sm font-medium">ZTForge</span>
        </Link>

        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowSimulator(!showSimulator)}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
              showSimulator
                ? "bg-amber-500/20 text-amber-300"
                : "text-zinc-500 hover:text-zinc-300 hover:bg-zinc-800"
            }`}
          >
            <Zap className="w-3.5 h-3.5" />
            Simulate
          </button>

          <div className="relative">
            <button
              onClick={() => setShowExport(!showExport)}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium text-zinc-500 hover:text-zinc-300 hover:bg-zinc-800 transition-colors"
            >
              <Download className="w-3.5 h-3.5" />
              Export
            </button>
            {showExport && (
              <div className="absolute right-0 top-full mt-1 bg-zinc-900 border border-zinc-800 rounded-lg shadow-xl py-1 min-w-[160px] z-50">
                {["rego", "pomerium", "terraform", "iptables"].map((fmt) => (
                  <button
                    key={fmt}
                    onClick={() => {
                      handleExport(fmt);
                      setShowExport(false);
                    }}
                    className="w-full text-left px-4 py-2 text-xs text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800 transition-colors capitalize"
                  >
                    {fmt === "rego" && "OPA Rego Policy"}
                    {fmt === "pomerium" && "Pomerium YAML"}
                    {fmt === "terraform" && "Terraform HCL"}
                    {fmt === "iptables" && "iptables Rules"}
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Canvas + optional side panel */}
      <div className="flex-1 flex relative overflow-hidden">
        <div className="flex-1">
          <Canvas
            canvasId={id}
            userId={userId}
            displayName={displayName}
          />
        </div>

        {showSimulator && (
          <div className="w-80 border-l border-zinc-800 bg-zinc-950 overflow-y-auto">
            <SimulatorPanel canvasId={id} />
          </div>
        )}
      </div>
    </div>
  );
}
