/**
 * Socket.io client with typed events, reconnect logic, and room management.
 */

import { io, Socket } from "socket.io-client";
import type { Position } from "./types";

let socket: Socket | null = null;
let reconnectAttempts = 0;
const MAX_RECONNECT_ATTEMPTS = 10;

export function getSocket(): Socket {
  if (!socket) {
    socket = io("/", {
      path: "/socket.io",
      transports: ["websocket", "polling"],
      reconnection: true,
      reconnectionDelay: 1000,
      reconnectionDelayMax: 5000,
      reconnectionAttempts: MAX_RECONNECT_ATTEMPTS,
    });

    socket.on("connect", () => {
      reconnectAttempts = 0;
      console.log("[ws] connected", socket?.id);
    });

    socket.on("disconnect", (reason) => {
      console.warn("[ws] disconnected:", reason);
    });

    socket.on("connect_error", (err) => {
      reconnectAttempts++;
      console.error(
        `[ws] connection error (attempt ${reconnectAttempts}):`,
        err.message,
      );
    });
  }

  return socket;
}

export function joinCanvas(
  canvasId: string,
  userId: string,
  displayName: string,
) {
  const s = getSocket();
  s.emit("canvas:join", {
    canvas_id: canvasId,
    user_id: userId,
    display_name: displayName,
  });
}

export function leaveCanvas(canvasId: string, userId: string) {
  const s = getSocket();
  s.emit("canvas:leave", { canvas_id: canvasId, user_id: userId });
}

export function emitCursorMove(
  canvasId: string,
  userId: string,
  position: Position,
) {
  const s = getSocket();
  s.volatile.emit("cursor:move", {
    canvas_id: canvasId,
    user_id: userId,
    position,
  });
}

export function emitNodeAdd(canvasId: string, node: Record<string, unknown>) {
  const s = getSocket();
  s.emit("node:add", { canvas_id: canvasId, node, event_type: "node:add" });
}

export function emitNodeMove(
  canvasId: string,
  nodeId: string,
  position: Position,
) {
  const s = getSocket();
  s.volatile.emit("node:move", {
    canvas_id: canvasId,
    node_id: nodeId,
    position,
    event_type: "node:move",
  });
}

export function emitNodeDelete(canvasId: string, nodeId: string) {
  const s = getSocket();
  s.emit("node:delete", {
    canvas_id: canvasId,
    node_id: nodeId,
    event_type: "node:delete",
  });
}

export function emitEdgeAdd(canvasId: string, edge: Record<string, unknown>) {
  const s = getSocket();
  s.emit("edge:add", { canvas_id: canvasId, edge, event_type: "edge:add" });
}

export function emitEdgeDelete(canvasId: string, edgeId: string) {
  const s = getSocket();
  s.emit("edge:delete", {
    canvas_id: canvasId,
    edge_id: edgeId,
    event_type: "edge:delete",
  });
}

export function disconnectSocket() {
  if (socket) {
    socket.disconnect();
    socket = null;
  }
}
