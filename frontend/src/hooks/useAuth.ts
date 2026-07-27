/**
 * useAuth — Keycloak OIDC authorization code flow with PKCE (S256).
 *
 * The ztforge-app Keycloak client requires PKCE (pkce.code.challenge.method=S256).
 * Flow:
 * 1. On load, check localStorage for a valid token.
 * 2. If none, check if the URL has ?code= (Keycloak callback).
 * 3. If code present, exchange it (+ PKCE verifier) for tokens via the backend.
 * 4. Otherwise, generate PKCE pair, store verifier, redirect to Keycloak.
 */

import { useEffect, useState } from "react";
import { setAccessToken } from "../lib/api";

const KEYCLOAK_URL = "http://localhost:8080";
const REALM = "ztforge";
const CLIENT_ID = "ztforge-app";
const REDIRECT_URI = `${window.location.origin}/`;

const AUTH_URL = `${KEYCLOAK_URL}/realms/${REALM}/protocol/openid-connect/auth`;
const TOKEN_EXCHANGE_URL = "/api/v1/auth/token";

interface AuthState {
  token: string | null;
  loading: boolean;
  error: string | null;
  user: { sub: string; email: string; display_name: string; role: string } | null;
}

// ── PKCE helpers ────────────────────────────────────────────────────────────

function randomBase64url(len: number): string {
  const arr = new Uint8Array(len);
  crypto.getRandomValues(arr);
  return btoa(String.fromCharCode(...arr))
    .replace(/\+/g, "-")
    .replace(/\//g, "_")
    .replace(/=+$/, "");
}

async function sha256Base64url(plain: string): Promise<string> {
  const encoder = new TextEncoder();
  const data = encoder.encode(plain);
  const digest = await crypto.subtle.digest("SHA-256", data);
  return btoa(String.fromCharCode(...new Uint8Array(digest)))
    .replace(/\+/g, "-")
    .replace(/\//g, "_")
    .replace(/=+$/, "");
}

async function buildLoginUrl(): Promise<string> {
  const verifier = randomBase64url(64);
  const challenge = await sha256Base64url(verifier);

  // Store verifier so we can use it after redirect back
  sessionStorage.setItem("pkce_verifier", verifier);

  const params = new URLSearchParams({
    client_id: CLIENT_ID,
    redirect_uri: REDIRECT_URI,
    response_type: "code",
    scope: "openid email profile",
    code_challenge: challenge,
    code_challenge_method: "S256",
  });
  return `${AUTH_URL}?${params.toString()}`;
}

// ── Hook ─────────────────────────────────────────────────────────────────────

export function useAuth(): AuthState & { login: () => void; logout: () => void } {
  const [state, setState] = useState<AuthState>({
    token: localStorage.getItem("zt_access_token"),
    loading: true,
    error: null,
    user: null,
  });

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const code = params.get("code");
    const storedToken = localStorage.getItem("zt_access_token");

    // Already have a token — validate it
    if (storedToken && !code) {
      setAccessToken(storedToken);
      fetchUser(storedToken);
      return;
    }

    // Keycloak redirected back with auth code
    if (code) {
      // Remove code from URL immediately
      window.history.replaceState({}, document.title, "/");

      const verifier = sessionStorage.getItem("pkce_verifier");
      sessionStorage.removeItem("pkce_verifier");

      fetch(TOKEN_EXCHANGE_URL, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          code,
          redirect_uri: REDIRECT_URI,
          code_verifier: verifier,
        }),
      })
        .then((r) => {
          if (!r.ok) return r.text().then((t) => { throw new Error(`Token exchange failed (${r.status}): ${t}`); });
          return r.json();
        })
        .then((data) => {
          localStorage.setItem("zt_access_token", data.access_token);
          if (data.refresh_token) {
            localStorage.setItem("zt_refresh_token", data.refresh_token);
          }
          setAccessToken(data.access_token);
          fetchUser(data.access_token);
        })
        .catch((err) => {
          setState((s) => ({ ...s, loading: false, error: err.message }));
        });
      return;
    }

    // No token, no code — show login screen
    setState((s) => ({ ...s, loading: false }));
  }, []);

  function fetchUser(token: string) {
    fetch("/api/v1/auth/me", {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then((r) => {
        if (!r.ok) {
          // Token expired or invalid — clear and show login
          localStorage.removeItem("zt_access_token");
          localStorage.removeItem("zt_refresh_token");
          setAccessToken(null);
          setState({ token: null, loading: false, error: null, user: null });
          return null;
        }
        return r.json();
      })
      .then((user) => {
        if (user) setState({ token, loading: false, error: null, user });
      })
      .catch(() => setState((s) => ({ ...s, loading: false })));
  }

  function login() {
    buildLoginUrl().then((url) => {
      window.location.href = url;
    });
  }

  function logout() {
    localStorage.removeItem("zt_access_token");
    localStorage.removeItem("zt_refresh_token");
    setAccessToken(null);
    const logoutUrl =
      `${KEYCLOAK_URL}/realms/${REALM}/protocol/openid-connect/logout` +
      `?client_id=${CLIENT_ID}&post_logout_redirect_uri=${encodeURIComponent(REDIRECT_URI)}`;
    window.location.href = logoutUrl;
  }

  return { ...state, login, logout };
}
