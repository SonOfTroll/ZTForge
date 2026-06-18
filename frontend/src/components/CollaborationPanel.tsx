/**
 * CollaborationPanel — shows active users in the canvas room.
 */

import type { CollabUser } from "../lib/types";

interface Props {
  collaborators: Record<string, CollabUser>;
}

export function CollaborationPanel({ collaborators }: Props) {
  const users = Object.values(collaborators);

  if (users.length === 0) return null;

  return (
    <div className="flex items-center gap-1 bg-zinc-900/90 backdrop-blur-sm border border-zinc-800 rounded-lg px-3 py-1.5">
      <div className="flex -space-x-2">
        {users.slice(0, 5).map((user) => (
          <div
            key={user.user_id}
            className="w-7 h-7 rounded-full border-2 border-zinc-900 flex items-center justify-center text-[10px] font-bold text-white"
            style={{ backgroundColor: user.color }}
            title={user.display_name}
          >
            {user.display_name.charAt(0).toUpperCase()}
          </div>
        ))}
      </div>
      {users.length > 5 && (
        <span className="text-[10px] text-zinc-500 ml-1">
          +{users.length - 5}
        </span>
      )}
      <span className="text-[10px] text-zinc-600 ml-2">
        {users.length} online
      </span>
    </div>
  );
}
