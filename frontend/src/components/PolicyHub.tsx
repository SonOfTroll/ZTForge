/**
 * PolicyHub — community template browser with search and fork.
 */

import { useEffect, useState } from "react";
import { BookOpen, GitFork, Tag, Search } from "lucide-react";
import { hubApi } from "../lib/api";
import type { Template } from "../lib/types";

export function PolicyHub() {
  const [templates, setTemplates] = useState<Template[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTag, setSearchTag] = useState("");

  useEffect(() => {
    loadTemplates();
  }, [searchTag]);

  async function loadTemplates() {
    setLoading(true);
    try {
      const data = await hubApi.list(searchTag ? { tag: searchTag } : {});
      setTemplates(data);
    } catch {
      // Non-critical — show empty state
    } finally {
      setLoading(false);
    }
  }

  async function handleFork(templateId: string) {
    try {
      await hubApi.fork(templateId);
      loadTemplates(); // Refresh to update fork counts
    } catch (e) {
      console.error("Fork failed:", e);
    }
  }

  return (
    <div className="flex flex-col gap-4">
      {/* Search */}
      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-zinc-500" />
        <input
          type="text"
          placeholder="Filter by tag…"
          value={searchTag}
          onChange={(e) => setSearchTag(e.target.value)}
          className="w-full bg-zinc-800 border border-zinc-700 rounded-lg pl-10 pr-4 py-2.5 text-sm text-zinc-200 placeholder-zinc-600 focus:outline-none focus:ring-1 focus:ring-blue-500/50"
        />
      </div>

      {/* Loading skeleton */}
      {loading && (
        <div className="flex flex-col gap-3">
          {[1, 2, 3].map((i) => (
            <div key={i} className="bg-zinc-800/50 rounded-xl p-4 animate-pulse">
              <div className="h-4 w-2/3 bg-zinc-700 rounded mb-2" />
              <div className="h-3 w-full bg-zinc-700/50 rounded" />
            </div>
          ))}
        </div>
      )}

      {/* Empty state */}
      {!loading && templates.length === 0 && (
        <div className="flex flex-col items-center gap-3 py-12 text-center">
          <BookOpen className="w-10 h-10 text-zinc-700" />
          <p className="text-sm text-zinc-500">No templates found</p>
          <p className="text-xs text-zinc-600">
            Be the first to share a Zero Trust template
          </p>
        </div>
      )}

      {/* Template list */}
      {!loading && templates.map((t) => (
        <div
          key={t.id}
          className="bg-zinc-800/30 border border-zinc-800 rounded-xl p-4 hover:border-zinc-700 transition-colors"
        >
          <div className="flex items-start justify-between gap-3">
            <div className="flex-1 min-w-0">
              <h4 className="text-sm font-medium text-zinc-200 truncate">
                {t.name}
              </h4>
              {t.description && (
                <p className="text-xs text-zinc-500 mt-1 line-clamp-2">
                  {t.description}
                </p>
              )}
            </div>
            <button
              onClick={() => handleFork(t.id)}
              className="flex items-center gap-1.5 text-xs text-zinc-400 hover:text-blue-400 bg-zinc-800 hover:bg-zinc-700 rounded-lg px-3 py-1.5 transition-colors flex-shrink-0"
            >
              <GitFork className="w-3 h-3" />
              Fork
            </button>
          </div>

          <div className="flex items-center gap-3 mt-3">
            <span className="flex items-center gap-1 text-[10px] text-zinc-600">
              <GitFork className="w-3 h-3" />
              {t.fork_count}
            </span>
            {t.tags.length > 0 && (
              <div className="flex items-center gap-1">
                <Tag className="w-3 h-3 text-zinc-600" />
                {t.tags.slice(0, 3).map((tag) => (
                  <span
                    key={tag}
                    className="text-[10px] text-zinc-500 bg-zinc-800 rounded px-1.5 py-0.5 cursor-pointer hover:text-zinc-400"
                    onClick={() => setSearchTag(tag)}
                  >
                    {tag}
                  </span>
                ))}
              </div>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}
