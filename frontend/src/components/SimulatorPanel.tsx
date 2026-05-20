/**
 * SimulatorPanel — breach simulation controls and results display.
 */

import { useState } from "react";
import { Zap, AlertTriangle, CheckCircle, XCircle } from "lucide-react";
import { simulationApi } from "../lib/api";
import type { SimulationResult, ScenarioInfo } from "../lib/types";

interface Props {
  canvasId: string;
  onSimulationResult?: (result: SimulationResult) => void;
}

const SCENARIOS: Record<string, ScenarioInfo> = {
  compromised_device: { name: "Compromised Device", description: "Endpoint compromised via malware" },
  stolen_credential: { name: "Stolen Credential", description: "Valid creds obtained via phishing" },
  insider_threat: { name: "Insider Threat", description: "Authenticated user, unauthorized access" },
  expired_certificate: { name: "Expired Certificate", description: "Stale session or expired cert" },
  lateral_from_dmz: { name: "Lateral from DMZ", description: "Foothold in DMZ, moving inward" },
  data_exfiltration: { name: "Data Exfiltration", description: "Attempt to extract classified data" },
  privilege_escalation: { name: "Privilege Escalation", description: "Service account exploitation" },
  supply_chain: { name: "Supply Chain", description: "Compromised third-party dependency" },
};

const riskColors: Record<string, string> = {
  critical: "text-red-400 bg-red-500/10",
  high: "text-orange-400 bg-orange-500/10",
  medium: "text-amber-400 bg-amber-500/10",
  low: "text-blue-400 bg-blue-500/10",
  minimal: "text-emerald-400 bg-emerald-500/10",
};

export function SimulatorPanel({ canvasId, onSimulationResult }: Props) {
  const [scenario, setScenario] = useState("stolen_credential");
  const [result, setResult] = useState<SimulationResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function runSimulation() {
    setLoading(true);
    setError(null);
    try {
      const res = await simulationApi.run({ canvas_id: canvasId, scenario });
      setResult(res);
      onSimulationResult?.(res);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Simulation failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex flex-col gap-4 p-4 bg-zinc-900 border border-zinc-800 rounded-xl max-w-sm">
      <div className="flex items-center gap-2">
        <Zap className="w-4 h-4 text-amber-400" />
        <h3 className="text-sm font-semibold text-zinc-200">Breach Simulator</h3>
      </div>

      {/* Scenario selector */}
      <div className="flex flex-col gap-2">
        <label className="text-xs text-zinc-500">Attack Scenario</label>
        <select
          value={scenario}
          onChange={(e) => setScenario(e.target.value)}
          className="bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-sm text-zinc-200 focus:outline-none focus:ring-1 focus:ring-blue-500/50"
        >
          {Object.entries(SCENARIOS).map(([key, info]) => (
            <option key={key} value={key}>
              {info.name}
            </option>
          ))}
        </select>
        <p className="text-[11px] text-zinc-600">
          {SCENARIOS[scenario]?.description}
        </p>
      </div>

      <button
        onClick={runSimulation}
        disabled={loading}
        className="flex items-center justify-center gap-2 bg-amber-500/20 hover:bg-amber-500/30 text-amber-300 rounded-lg px-4 py-2.5 text-sm font-medium transition-colors disabled:opacity-50"
      >
        {loading ? (
          <div className="w-4 h-4 border-2 border-amber-500/30 border-t-amber-400 rounded-full animate-spin" />
        ) : (
          <Zap className="w-4 h-4" />
        )}
        {loading ? "Simulating…" : "Run Simulation"}
      </button>

      {error && (
        <div className="flex items-center gap-2 text-red-400 text-xs bg-red-500/10 rounded-lg px-3 py-2">
          <XCircle className="w-3.5 h-3.5 flex-shrink-0" />
          {error}
        </div>
      )}

      {/* Results */}
      {result && (
        <div className="flex flex-col gap-3 mt-2">
          {/* Risk score */}
          <div className={`flex items-center justify-between rounded-lg px-3 py-2 ${riskColors[result.risk_level]}`}>
            <span className="text-xs font-medium">Risk Score</span>
            <span className="text-lg font-bold">{result.risk_score}</span>
          </div>

          {/* Summary stats */}
          <div className="grid grid-cols-2 gap-2">
            <div className="bg-zinc-800/50 rounded-lg px-3 py-2">
              <div className="text-[10px] text-zinc-500">Steps</div>
              <div className="text-sm font-medium text-zinc-300">
                {result.successful_steps}/{result.total_steps}
              </div>
            </div>
            <div className="bg-zinc-800/50 rounded-lg px-3 py-2">
              <div className="text-[10px] text-zinc-500">Compromised</div>
              <div className="text-sm font-medium text-zinc-300">
                {result.compromised_nodes.length} nodes
              </div>
            </div>
          </div>

          {/* Attack path */}
          {result.attack_path.length > 0 && (
            <div className="flex flex-col gap-1">
              <span className="text-xs text-zinc-500 font-medium">Attack Path</span>
              <div className="flex flex-col gap-0.5 max-h-40 overflow-y-auto">
                {result.attack_path.map((step) => (
                  <div
                    key={step.step_number}
                    className="flex items-start gap-2 text-[11px] py-1 px-2 rounded bg-zinc-800/30"
                  >
                    {step.result === "allowed" ? (
                      <AlertTriangle className="w-3 h-3 text-amber-400 mt-0.5 flex-shrink-0" />
                    ) : (
                      <CheckCircle className="w-3 h-3 text-emerald-400 mt-0.5 flex-shrink-0" />
                    )}
                    <span className="text-zinc-400">{step.reason}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Recommendations */}
          {result.recommendations.length > 0 && (
            <div className="flex flex-col gap-1">
              <span className="text-xs text-zinc-500 font-medium">Recommendations</span>
              {result.recommendations.map((rec, i) => (
                <p key={i} className="text-[11px] text-zinc-400 pl-2 border-l border-blue-500/30">
                  {rec}
                </p>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
