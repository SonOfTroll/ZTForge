/**
 * useCanvas hook — manages canvas state, persistence, and real-time sync.
 *
 * This is the main state management hook for the canvas. It handles:
 * - Loading canvas data from the API
 * - Optimistic updates with server reconciliation
 * - Socket.io event subscriptions for real-time collaboration
 * - Debounced auto-save
 */

import { useCallback, useEffect, useRef, useState } from "react";
import {
  useNodesState,
  useEdgesState,
  type Node,
  type Edge,
  type OnConnect,
  type OnNodesChange,
  type OnEdgesChange,
  addEdge,
} from "@xyflow/react";
import { canvasApi } from "../lib/api";
import { getSocket, joinCanvas, leaveCanvas, emitNodeMove } from "../lib/socket";
import type { Canvas, CollabUser } from "../lib/types";

interface UseCanvasOptions {
  canvasId: string;
  userId: string;
  displayName: string;
}

export function useCanvas({ canvasId, userId, displayName }: UseCanvasOptions) {
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  const [canvas, setCanvas] = useState<Canvas | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [collaborators, setCollaborators] = useState<Record<string, CollabUser>>({});
  const [saving, setSaving] = useState(false);
  const versionRef = useRef(1);
  const saveTimerRef = useRef<ReturnType<typeof setTimeout>>();

  // Load canvas from API
  useEffect(() => {
    let cancelled = false;

    async function load() {
      try {
        setLoading(true);
        const data = await canvasApi.get(canvasId);
        if (cancelled) return;

        setCanvas(data);
        versionRef.current = data.version;

        // Map backend nodes to React Flow nodes
        const rfNodes: Node[] = (data.nodes || []).map((n: Record<string, unknown>) => ({
          id: n.id as string,
          type: (n.data as Record<string, unknown>)?.node_type as string || "identity",
          position: n.position as { x: number; y: number },
          data: n.data,
        }));
        setNodes(rfNodes);

        const rfEdges: Edge[] = (data.edges || []).map((e: Record<string, unknown>) => ({
          id: e.id as string,
          source: e.source as string,
          target: e.target as string,
          label: e.label as string | undefined,
          animated: e.animated as boolean | undefined,
          data: { policy: e.policy },
        }));
        setEdges(rfEdges);
        setError(null);
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : "Failed to load canvas");
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    load();
    return () => { cancelled = true; };
  }, [canvasId, setNodes, setEdges]);

  // Socket.io: join room and listen for events
  useEffect(() => {
    const socket = getSocket();
    joinCanvas(canvasId, userId, displayName);

    socket.on("presence:state", (data: { users: Record<string, CollabUser> }) => {
      setCollaborators(data.users);
    });

    socket.on("presence:join", (user: CollabUser) => {
      setCollaborators((prev) => ({ ...prev, [user.user_id]: user }));
    });

    socket.on("presence:leave", (data: { user_id: string }) => {
      setCollaborators((prev) => {
        const next = { ...prev };
        delete next[data.user_id];
        return next;
      });
    });

    socket.on("node:add", (data: { node: Record<string, unknown> }) => {
      const n = data.node;
      setNodes((nds) => [
        ...nds,
        {
          id: n.id as string,
          type: (n.data as Record<string, unknown>)?.node_type as string || "identity",
          position: n.position as { x: number; y: number },
          data: n.data,
        } as Node,
      ]);
    });

    socket.on("node:move", (data: { node_id: string; position: { x: number; y: number } }) => {
      setNodes((nds) =>
        nds.map((n) => (n.id === data.node_id ? { ...n, position: data.position } : n)),
      );
    });

    socket.on("node:delete", (data: { node_id: string }) => {
      setNodes((nds) => nds.filter((n) => n.id !== data.node_id));
    });

    socket.on("edge:add", (data: { edge: Record<string, unknown> }) => {
      const e = data.edge;
      setEdges((eds) => [
        ...eds,
        { id: e.id as string, source: e.source as string, target: e.target as string } as Edge,
      ]);
    });

    socket.on("edge:delete", (data: { edge_id: string }) => {
      setEdges((eds) => eds.filter((e) => e.id !== data.edge_id));
    });

    return () => {
      leaveCanvas(canvasId, userId);
      socket.off("presence:state");
      socket.off("presence:join");
      socket.off("presence:leave");
      socket.off("node:add");
      socket.off("node:move");
      socket.off("node:delete");
      socket.off("edge:add");
      socket.off("edge:delete");
    };
  }, [canvasId, userId, displayName, setNodes, setEdges]);

  // Debounced auto-save
  const scheduleSave = useCallback(() => {
    if (saveTimerRef.current) clearTimeout(saveTimerRef.current);
    saveTimerRef.current = setTimeout(async () => {
      try {
        setSaving(true);
        const nodeData = nodes.map((n) => ({
          id: n.id,
          type: n.type,
          position: n.position,
          data: n.data,
        }));
        const edgeData = edges.map((e) => ({
          id: e.id,
          source: e.source,
          target: e.target,
          label: e.label,
          policy: (e.data as Record<string, unknown>)?.policy,
        }));
        const updated = await canvasApi.update(canvasId, {
          nodes: nodeData,
          edges: edgeData,
          version: versionRef.current,
        });
        versionRef.current = updated.version;
      } catch {
        // Version conflict or network error — don't crash, user can retry
        console.warn("[canvas] auto-save failed");
      } finally {
        setSaving(false);
      }
    }, 2000);
  }, [canvasId, nodes, edges]);

  const onConnect: OnConnect = useCallback(
    (connection) => {
      setEdges((eds) => addEdge({ ...connection, animated: true }, eds));
      scheduleSave();
    },
    [setEdges, scheduleSave],
  );

  const handleNodesChange: OnNodesChange = useCallback(
    (changes) => {
      onNodesChange(changes);
      // Broadcast position changes for real-time sync
      for (const change of changes) {
        if (change.type === "position" && change.position) {
          emitNodeMove(canvasId, change.id, change.position);
        }
      }
      scheduleSave();
    },
    [onNodesChange, canvasId, scheduleSave],
  );

  const handleEdgesChange: OnEdgesChange = useCallback(
    (changes) => {
      onEdgesChange(changes);
      scheduleSave();
    },
    [onEdgesChange, scheduleSave],
  );

  return {
    nodes,
    edges,
    onNodesChange: handleNodesChange,
    onEdgesChange: handleEdgesChange,
    onConnect,
    canvas,
    loading,
    error,
    saving,
    collaborators,
    setNodes,
    setEdges,
  };
}
