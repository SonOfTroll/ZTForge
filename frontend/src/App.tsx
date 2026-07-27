import { BrowserRouter, Routes, Route } from "react-router-dom";
import { Dashboard } from "./pages/Dashboard";
import { CanvasPage } from "./pages/CanvasPage";
import { HubPage } from "./pages/HubPage";
import { useAuth } from "./hooks/useAuth";

function AuthGate({ children }: { children: React.ReactNode }) {
  const { token, loading, error, login } = useAuth();

  if (loading) {
    return (
      <div className="min-h-screen bg-zinc-950 flex items-center justify-center">
        <div className="flex flex-col items-center gap-4">
          <div className="w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
          <p className="text-zinc-500 text-sm">Authenticating…</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-zinc-950 flex items-center justify-center">
        <div className="text-center max-w-sm">
          <p className="text-red-400 text-sm mb-4">Auth error: {error}</p>
          <button
            onClick={login}
            className="bg-blue-600 hover:bg-blue-500 text-white rounded-lg px-4 py-2 text-sm transition-colors"
          >
            Try again
          </button>
        </div>
      </div>
    );
  }

  if (!token) {
    return (
      <div className="min-h-screen bg-zinc-950 flex items-center justify-center">
        <div className="text-center max-w-sm">
          <div className="flex items-center justify-center gap-2 mb-6">
            <svg className="w-8 h-8 text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12.75L11.25 15 15 9.75m-3-7.036A11.959 11.959 0 013.598 6 11.955 11.955 0 01.44 8.882C.147 9.584 0 10.315 0 11.063c0 5.014 3.357 9.375 8 10.937C12.643 20.438 16 16.077 16 11.063c0-.748-.147-1.479-.44-2.181A11.955 11.955 0 0112.402 6 11.959 11.959 0 019 2.714z" />
            </svg>
            <span className="text-xl font-semibold text-zinc-100">ZTForge</span>
          </div>
          <p className="text-zinc-500 text-sm mb-6">
            Sign in to design and simulate your Zero Trust architecture.
          </p>
          <button
            onClick={login}
            className="w-full bg-blue-600 hover:bg-blue-500 text-white rounded-lg px-6 py-2.5 text-sm font-medium transition-colors"
          >
            Sign in with Keycloak
          </button>
        </div>
      </div>
    );
  }

  return <>{children}</>;
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthGate>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/canvas/:id" element={<CanvasPage />} />
          <Route path="/hub" element={<HubPage />} />
        </Routes>
      </AuthGate>
    </BrowserRouter>
  );
}
