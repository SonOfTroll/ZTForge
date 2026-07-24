/**
 * Domain types shared across the frontend.
 * These mirror the backend Pydantic schemas.
 */

// ── Canvas Types ────────────────────────────────────────────

export interface Position {
  x: number;
  y: number;
}

export type ZTNodeType =
  | "identity"
  | "device"
  | "application"
  | "data"
  | "network_segment"
  | "policy_gate";

export interface NodeData {
  label: string;
  node_type: "identity" | "device" | "application" | "data" | "network_segment" | "policy_gate";
  compliance_status?: string;
  classification?: string;
  [key: string]: unknown;
}

export interface EdgePolicy {
  action: "allow" | "deny";
  conditions: Record<string, unknown>;
}

export interface CanvasEdge {
  id: string;
  source: string;
  target: string;
  label?: string;
  animated?: boolean;
  policy?: EdgePolicy;
}

export interface Canvas {
  id: string;
  title: string;
  description?: string;
  nodes: CanvasNodeRaw[];
  edges: CanvasEdge[];
  viewport: { x: number; y: number; zoom: number };
  version: number;
  visibility: "private" | "team" | "public";
  owner_id: string;
  created_at: string;
  updated_at: string;
}

export interface CanvasNodeRaw {
  id: string;
  type: string;
  position: Position;
  data: NodeData;
  width?: number;
  height?: number;
}

// ── Simulation Types ────────────────────────────────────────

export interface AttackStep {
  step_number: number;
  from_node: string;
  to_node: string;
  edge_id?: string;
  action: string;
  result: "allowed" | "blocked" | "partial";
  reason: string;
  risk_contribution: number;
}

export interface SimulationResult {
  simulation_id: string;
  scenario: string;
  risk_score: number;
  risk_level: "critical" | "high" | "medium" | "low" | "minimal";
  attack_path: AttackStep[];
  blocked_at?: AttackStep;
  total_steps: number;
  successful_steps: number;
  highlighted_nodes: string[];
  highlighted_edges: string[];
  compromised_nodes: string[];
  recommendations: string[];
  summary: string;
}

export interface ScenarioInfo {
  name: string;
  description: string;
}

// ── Collaboration Types ─────────────────────────────────────

export interface CollabUser {
  user_id: string;
  display_name: string;
  color: string;
  cursor?: Position;
}

// ── Socket Events ───────────────────────────────────────────

export interface SocketEvents {
  "canvas:join": { canvas_id: string; user_id: string; display_name: string };
  "canvas:leave": { canvas_id: string; user_id: string };
  "cursor:move": { canvas_id: string; user_id: string; position: Position };
  "cursor:update": { user_id: string; position: Position };
  "presence:join": CollabUser;
  "presence:leave": { user_id: string };
  "presence:state": { users: Record<string, CollabUser> };
  "node:add": { canvas_id: string; node: CanvasNodeRaw; event_type: string };
  "node:move": { canvas_id: string; node_id: string; position: Position; event_type: string };
  "node:delete": { canvas_id: string; node_id: string; event_type: string };
  "edge:add": { canvas_id: string; edge: CanvasEdge; event_type: string };
  "edge:delete": { canvas_id: string; edge_id: string; event_type: string };
  "comment:add": { canvas_id: string; node_id: string; text: string; user_id: string };
  "comment:new": { canvas_id: string; node_id: string; text: string; user_id: string };
}

// ── Template Types ──────────────────────────────────────────

export interface Template {
  id: string;
  name: string;
  description?: string;
  tags: string[];
  canvas_data: Record<string, unknown>;
  policies_data: Record<string, unknown>[];
  forked_from?: string;
  fork_count: number;
  visibility: string;
  author_id: string;
  created_at: string;
  updated_at: string;
}
