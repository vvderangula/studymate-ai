import { useEffect, useState, type ReactNode } from "react";

import { IconTrash } from "./icons";

export interface HistoryEntry {
  id: string;
  title: string;
  /** Second line, e.g. "17 pages" or a message preview. */
  subtitle?: string;
  /** Right-aligned meta, e.g. "3h ago". */
  meta?: string;
}

/**
 * A saved-items card for a workspace aside: PDFs, videos, chats, quizzes…
 * Selecting an item reopens it; deleting asks for a second click to confirm.
 */
export default function HistoryList({
  title,
  items,
  selectedId,
  loading = false,
  emptyText,
  onSelect,
  onDelete,
  action,
}: {
  title: string;
  items: HistoryEntry[];
  selectedId?: string | null;
  loading?: boolean;
  emptyText: string;
  onSelect: (id: string) => void;
  onDelete?: (id: string) => void;
  /** Optional header control, e.g. a "New chat" button. */
  action?: ReactNode;
}) {
  const [confirming, setConfirming] = useState<string | null>(null);

  // A pending "Delete?" quietly cancels itself.
  useEffect(() => {
    if (!confirming) return;
    const timer = window.setTimeout(() => setConfirming(null), 3500);
    return () => window.clearTimeout(timer);
  }, [confirming]);

  return (
    <section className="card overflow-hidden" aria-label={title}>
      <div className="flex min-h-12 items-center justify-between gap-2 border-b border-line px-4 py-2">
        <h2 className="section-title">
          {title}
          {items.length > 0 && (
            <span className="ml-2 text-xs font-normal tabular-nums text-muted">{items.length}</span>
          )}
        </h2>
        {action}
      </div>

      {loading ? (
        <div className="space-y-2 p-3" role="status" aria-label={`Loading ${title.toLowerCase()}`}>
          {[0, 1, 2].map((row) => (
            <div key={row} className="skeleton h-12" />
          ))}
        </div>
      ) : items.length === 0 ? (
        <p className="px-4 py-6 text-center text-sm leading-6 text-muted">{emptyText}</p>
      ) : (
        <ul className="max-h-[22rem] space-y-1 overflow-y-auto overscroll-contain p-2">
          {items.map((item) => {
            const selected = item.id === selectedId;
            const askingDelete = confirming === item.id;
            return (
              <li key={item.id} className="group relative">
                <button
                  type="button"
                  onClick={() => onSelect(item.id)}
                  aria-current={selected ? "true" : undefined}
                  className={
                    "w-full rounded-panel py-2.5 pl-3 text-left transition-[background-color,box-shadow] duration-150 " +
                    (onDelete ? "pr-10 " : "pr-3 ") +
                    (selected
                      ? "bg-gradient-to-br from-accent-soft to-accent-tint/60 ring-1 ring-inset ring-accent-line"
                      : "hover:bg-sunken/70")
                  }
                >
                  <span className="flex items-baseline justify-between gap-3">
                    <span
                      className={
                        "min-w-0 truncate text-sm font-medium " +
                        (selected ? "text-accent-ink" : "text-ink")
                      }
                      title={item.title}
                    >
                      {item.title}
                    </span>
                    {item.meta && (
                      <span className="shrink-0 text-xs tabular-nums text-muted">{item.meta}</span>
                    )}
                  </span>
                  {item.subtitle && (
                    <span className="mt-0.5 block truncate text-xs text-muted">{item.subtitle}</span>
                  )}
                </button>

                {onDelete &&
                  (askingDelete ? (
                    <button
                      type="button"
                      onClick={() => {
                        setConfirming(null);
                        onDelete(item.id);
                      }}
                      className="absolute right-2 top-1/2 z-10 h-8 -translate-y-1/2 rounded-control bg-danger px-2.5 text-xs font-semibold text-white shadow-card"
                    >
                      Delete?
                    </button>
                  ) : (
                    <button
                      type="button"
                      onClick={() => setConfirming(item.id)}
                      aria-label={`Delete ${item.title}`}
                      className="absolute right-2 top-1/2 flex h-8 w-8 -translate-y-1/2 items-center justify-center rounded-control text-faint opacity-100 transition-[opacity,color,background-color] hover:bg-danger-soft hover:text-danger focus-visible:opacity-100 sm:opacity-0 sm:group-hover:opacity-100"
                    >
                      <IconTrash className="h-4 w-4" />
                    </button>
                  ))}
              </li>
            );
          })}
        </ul>
      )}
    </section>
  );
}
