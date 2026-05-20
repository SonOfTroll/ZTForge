/**
 * Canvas component — the core workspace using React Flow.
 */

import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  BackgroundVariant,
  Panel,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";

import { nodeTypes } from "./NodeTypes";
import { useCanvas } from "../hooks/useCanvas";
import { Toolbar } from "./Toolbar";
import { CollaborationPanel } from "./CollaborationPanel";

interface CanvasProps {
  canvasId: string;
  userId: string;
  displayName: string;
}

export function Canvas({ canvasId, userId, displayName }: CanvasProps) {
  const {
    nodes,
    edges,
    onNodesChange,
    onEdgesChange,
    onConnect,
    canvas,
    loading,
    error,
    saving,
    collaborators,
    setNodes,
  } = useCanvas({ canvasId, userId, displayName });

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full bg-zinc-950">
        <div className="flex flex-col items-center gap-3">
          <div className="w-8 h-8 border-2 border-zinc-700 border-t-blue-500 rounded-full animate-spin" />
          <span className="text-sm text-zinc-500">Loading canvas…</span>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-full bg-zinc-950">
        <div className="text-center">
          <p className="text-red-400 font-medium">Failed to load canvas</p>
          <p className="text-sm text-zinc-500 mt-1">{error}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="h-full w-full relative">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onConnect={onConnect}
        nodeTypes={nodeTypes}
        fitView
        snapToGrid
        snapGrid={[16, 16]}
        className="bg-zinc-950"
        defaultEdgeOptions={{
          animated: true,
          style: { stroke: "#52525b", strokeWidth: 2 },
        }}
        proOptions={{ hideAttribution: true }}
      >
        <Background
          variant={BackgroundVariant.Dots}
          gap={20}
          size={1}
          color="#27272a"
        />
        <Controls
          className="!bg-zinc-900 !border-zinc-800 !rounded-lg !shadow-xl [&>button]:!bg-zinc-800 [&>button]:!border-zinc-700 [&>button]:!text-zinc-400 [&>button:hover]:!bg-zinc-700"
        />
        <MiniMap
          nodeColor={(node) => {
            const colors: Record<string, string> = {
              identity: "#3b82f6",
              device: "#f59e0b",
              application: "#10b981",
              data: "#8b5cf6",
              network_segment: "#06b6d4",
              policy_gate: "#f43f5e",
            };
            return colors[node.type || ""] || "#71717a";
          }}
          className="!bg-zinc-900/80 !border-zinc-800 !rounded-lg"
          maskColor="rgba(0,0,0,0.7)"
        />

        {/* Top-left: Canvas title + save status */}
        <Panel position="top-left">
          <div className="flex items-center gap-3 bg-zinc-900/90 backdrop-blur-sm border border-zinc-800 rounded-lg px-4 py-2">
            <h2 className="text-sm font-semibold text-zinc-200">
              {canvas?.title || "Untitled"}
            </h2>
            {saving && (
              <span className="text-[10px] text-zinc-500 flex items-center gap-1">
                <span className="w-1.5 h-1.5 bg-amber-400 rounded-full animate-pulse" />
                Saving
              </span>
            )}
            {!saving && (
              <span className="text-[10px] text-zinc-600">v{canvas?.version}</span>
            )}
          </div>
        </Panel>

        {/* Top-right: Collaborators */}
        <Panel position="top-right">
          <CollaborationPanel collaborators={collaborators} />
        </Panel>
      </ReactFlow>

      {/* Left sidebar: Toolbar */}
      <div className="absolute left-3 top-1/2 -translate-y-1/2 z-10">
        <Toolbar canvasId={canvasId} setNodes={setNodes} />
      </div>
    </div>
  );
}
