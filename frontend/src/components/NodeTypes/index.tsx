/**
 * Custom React Flow node types for Zero Trust architecture elements.
 *
 * Each node type has a distinct visual identity so the canvas is
 * immediately readable. Colors and icons map to security concepts.
 */

import { Handle, Position, type NodeProps } from "@xyflow/react";
import {
  User,
  Monitor,
  Server,
  Database,
  Network,
  ShieldCheck,
} from "lucide-react";
import type { NodeData } from "../../lib/types";

const nodeStyles = {
  identity: {
    bg: "bg-blue-500/10",
    border: "border-blue-500/40",
    icon: User,
    accent: "text-blue-400",
    glow: "shadow-blue-500/20",
  },
  device: {
    bg: "bg-amber-500/10",
    border: "border-amber-500/40",
    icon: Monitor,
    accent: "text-amber-400",
    glow: "shadow-amber-500/20",
  },
  application: {
    bg: "bg-emerald-500/10",
    border: "border-emerald-500/40",
    icon: Server,
    accent: "text-emerald-400",
    glow: "shadow-emerald-500/20",
  },
  data: {
    bg: "bg-purple-500/10",
    border: "border-purple-500/40",
    icon: Database,
    accent: "text-purple-400",
    glow: "shadow-purple-500/20",
  },
  network_segment: {
    bg: "bg-cyan-500/10",
    border: "border-cyan-500/40",
    icon: Network,
    accent: "text-cyan-400",
    glow: "shadow-cyan-500/20",
  },
  policy_gate: {
    bg: "bg-rose-500/10",
    border: "border-rose-500/40",
    icon: ShieldCheck,
    accent: "text-rose-400",
    glow: "shadow-rose-500/20",
  },
} as const;

function ZTNode({ data, selected }: NodeProps & { data: NodeData }) {
  const style = nodeStyles[data.node_type] || nodeStyles.identity;
  const Icon = style.icon;

  return (
    <div
      className={`
        relative px-4 py-3 rounded-xl border backdrop-blur-sm
        transition-all duration-200 min-w-[160px]
        ${style.bg} ${style.border}
        ${selected ? `ring-2 ring-white/30 shadow-lg ${style.glow}` : "shadow-md"}
        hover:shadow-lg
      `}
    >
      <Handle
        type="target"
        position={Position.Left}
        className="!w-3 !h-3 !bg-zinc-400 !border-zinc-600"
      />

      <div className="flex items-center gap-2.5">
        <div className={`p-1.5 rounded-lg ${style.bg}`}>
          <Icon className={`w-4 h-4 ${style.accent}`} />
        </div>
        <div className="flex flex-col min-w-0">
          <span className="text-xs font-medium text-zinc-200 truncate">
            {data.label}
          </span>
          <span className="text-[10px] text-zinc-500 capitalize">
            {data.node_type.replace("_", " ")}
          </span>
        </div>
      </div>

      {data.compliance_status && (
        <div
          className={`
            absolute -top-1 -right-1 w-3 h-3 rounded-full border border-zinc-800
            ${data.compliance_status === "compliant" ? "bg-emerald-400" : "bg-red-400"}
          `}
          title={`Device: ${data.compliance_status}`}
        />
      )}

      {data.classification && (
        <div className="mt-1.5 text-[9px] font-mono text-zinc-500 uppercase tracking-wider">
          {data.classification}
        </div>
      )}

      <Handle
        type="source"
        position={Position.Right}
        className="!w-3 !h-3 !bg-zinc-400 !border-zinc-600"
      />
    </div>
  );
}

// Export individual node type components for React Flow registration
export function IdentityNode(props: NodeProps) {
  return <ZTNode {...props} data={{ ...props.data, node_type: props.data.node_type || "identity" } as NodeData} />;
}

export function DeviceNode(props: NodeProps) {
  return <ZTNode {...props} data={{ ...props.data, node_type: props.data.node_type || "device" } as NodeData} />;
}

export function AppNode(props: NodeProps) {
  return <ZTNode {...props} data={{ ...props.data, node_type: props.data.node_type || "application" } as NodeData} />;
}

export function DataNode(props: NodeProps) {
  return <ZTNode {...props} data={{ ...props.data, node_type: props.data.node_type || "data" } as NodeData} />;
}

export function NetworkSegmentNode(props: NodeProps) {
  return <ZTNode {...props} data={{ ...props.data, node_type: props.data.node_type || "network_segment" } as NodeData} />;
}

export function PolicyGateNode(props: NodeProps) {
  return <ZTNode {...props} data={{ ...props.data, node_type: props.data.node_type || "policy_gate" } as NodeData} />;
}

// Node type registry for React Flow
export const nodeTypes = {
  identity: IdentityNode,
  device: DeviceNode,
  application: AppNode,
  data: DataNode,
  network_segment: NetworkSegmentNode,
  policy_gate: PolicyGateNode,
};
