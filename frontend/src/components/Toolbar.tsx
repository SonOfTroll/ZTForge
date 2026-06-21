/**
 * Toolbar — drag source for adding nodes to the canvas.
 */

import { useCallback } from "react";
import type { Node } from "@xyflow/react";
import {
  User,
  Monitor,
  Server,
  Database,
  Network,
  ShieldCheck,
} from "lucide-react";
import type { ZTNodeType } from "../lib/types";
import { emitNodeAdd } from "../lib/socket";

const tools: { type: ZTNodeType; label: string; icon: typeof User }[] = [
  { type: "identity", label: "Identity", icon: User },
  { type: "device", label: "Device", icon: Monitor },
  { type: "application", label: "App", icon: Server },
  { type: "data", label: "Data", icon: Database },
  { type: "network_segment", label: "Segment", icon: Network },
  { type: "policy_gate", label: "Gate", icon: ShieldCheck },
];

interface ToolbarProps {
  canvasId: string;
  setNodes: React.Dispatch<React.SetStateAction<Node[]>>;
}

export function Toolbar({ canvasId, setNodes }: ToolbarProps) {
  const addNode = useCallback(
    (type: ZTNodeType, label: string) => {
      const id = `${type}-${Date.now()}`;
      // Slight randomness in position so nodes don't stack
      const position = {
        x: 200 + Math.random() * 200,
        y: 150 + Math.random() * 200,
      };

      const nodeData = {
        label: `New ${label}`,
        node_type: type,
        properties: {},
      };

      const newNode: Node = {
        id,
        type,
        position,
        data: nodeData,
      };

      setNodes((nds) => [...nds, newNode]);
      emitNodeAdd(canvasId, { id, type, position, data: nodeData });
    },
    [canvasId, setNodes],
  );

  return (
    <div className="flex flex-col gap-1.5 bg-zinc-900/90 backdrop-blur-sm border border-zinc-800 rounded-xl p-2 shadow-xl">
      {tools.map(({ type, label, icon: Icon }) => (
        <button
          key={type}
          onClick={() => addNode(type, label)}
          className="
            group flex items-center gap-2 px-3 py-2 rounded-lg
            text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800
            transition-colors duration-150
          "
          title={`Add ${label} node`}
        >
          <Icon className="w-4 h-4" />
          <span className="text-xs font-medium hidden group-hover:inline">
            {label}
          </span>
        </button>
      ))}
    </div>
  );
}
