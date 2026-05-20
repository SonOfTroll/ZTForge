/**
 * API client with typed methods, error handling, and token management.
 */

const API_BASE = "/api/v1";

class ApiError extends Error {
  constructor(
    public status: number,
    public detail: string,
  ) {
    super(`API Error ${status}: ${detail}`);
    this.name = "ApiError";
  }
}

let accessToken: string | null = null;

export function setAccessToken(token: string | null) {
  accessToken = token;
}

async function request<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };

  if (accessToken) {
    headers["Authorization"] = `Bearer ${accessToken}`;
  }

  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers,
  });

  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }));
    throw new ApiError(res.status, body.detail || res.statusText);
  }

  if (res.status === 204) return undefined as T;
  return res.json();
}

// ── Canvas API ──────────────────────────────────────────────

import type { Canvas, SimulationResult, Template } from "./types";

export const canvasApi = {
  list: () => request<Canvas[]>("/canvases"),

  get: (id: string) => request<Canvas>(`/canvases/${id}`),

  create: (data: { title: string; description?: string }) =>
    request<Canvas>("/canvases", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  update: (id: string, data: Record<string, unknown>) =>
    request<Canvas>(`/canvases/${id}`, {
      method: "PATCH",
      body: JSON.stringify(data),
    }),

  delete: (id: string) =>
    request<void>(`/canvases/${id}`, { method: "DELETE" }),
};

// ── Simulation API ──────────────────────────────────────────

export const simulationApi = {
  run: (data: {
    canvas_id: string;
    scenario: string;
    source_node_id?: string;
    target_node_id?: string;
    attacker_properties?: Record<string, unknown>;
  }) =>
    request<SimulationResult>("/simulation/run", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  scenarios: () =>
    request<Record<string, { name: string; description: string }>>(
      "/simulation/scenarios",
    ),
};

// ── Hub API ─────────────────────────────────────────────────

export const hubApi = {
  list: (params?: { tag?: string; limit?: number }) => {
    const query = new URLSearchParams();
    if (params?.tag) query.set("tag", params.tag);
    if (params?.limit) query.set("limit", String(params.limit));
    const qs = query.toString();
    return request<Template[]>(`/hub/templates${qs ? `?${qs}` : ""}`);
  },

  fork: (id: string, name?: string) =>
    request<Template>(`/hub/templates/${id}/fork`, {
      method: "POST",
      body: JSON.stringify({ name }),
    }),

  export: (canvasId: string, format: string) =>
    fetch(`${API_BASE}/hub/export/${canvasId}?format=${format}`, {
      headers: accessToken ? { Authorization: `Bearer ${accessToken}` } : {},
    }).then((r) => r.text()),
};
