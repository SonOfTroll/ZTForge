/**
 * HubPage — community policy template marketplace.
 */

import { Link } from "react-router-dom";
import { ArrowLeft, ShieldCheck } from "lucide-react";
import { PolicyHub } from "../components/PolicyHub";

export function HubPage() {
  return (
    <div className="min-h-screen bg-zinc-950 text-zinc-200">
      <header className="border-b border-zinc-800/50 bg-zinc-950/80 backdrop-blur-sm sticky top-0 z-50">
        <div className="max-w-4xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Link to="/" className="text-zinc-500 hover:text-zinc-300 transition-colors">
              <ArrowLeft className="w-4 h-4" />
            </Link>
            <ShieldCheck className="w-5 h-5 text-blue-400" />
            <span className="text-lg font-semibold">Policy Hub</span>
          </div>
        </div>
      </header>

      <main className="max-w-4xl mx-auto px-6 py-8">
        <div className="mb-8">
          <h1 className="text-2xl font-bold tracking-tight mb-2">
            Community Templates
          </h1>
          <p className="text-sm text-zinc-500">
            Browse, fork, and customize Zero Trust policy templates shared by
            the community.
          </p>
        </div>
        <PolicyHub />
      </main>
    </div>
  );
}
