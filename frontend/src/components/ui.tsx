import type { ReactNode } from "react";
import { IconAlert, IconCheck } from "./icons";

/** Inline error message. Keeps role="alert" so screen readers announce it. */
export function ErrorNotice({
  children,
  className = "",
}: {
  children: ReactNode;
  className?: string;
}) {
  return (
    <div role="alert" className={`notice-error ${className}`}>
      <IconAlert className="mt-0.5 h-4 w-4 shrink-0" />
      <span className="min-w-0 break-words">{children}</span>
    </div>
  );
}

/** Inline success message (role="status"). */
export function SuccessNotice({
  children,
  className = "",
}: {
  children: ReactNode;
  className?: string;
}) {
  return (
    <p role="status" className={`notice-success ${className}`}>
      <IconCheck className="mt-0.5 h-4 w-4 shrink-0" />
      <span className="min-w-0 break-words">{children}</span>
    </p>
  );
}

/** Neutral in-progress message with a small spinner (role="status"). */
export function ProgressNotice({
  children,
  className = "",
}: {
  children: ReactNode;
  className?: string;
}) {
  return (
    <p role="status" className={`notice-muted ${className}`}>
      <span className="spinner text-faint" aria-hidden="true" />
      <span className="min-w-0">{children}</span>
    </p>
  );
}

/** Assistant-side "working" bubble with three pulsing dots (role="status"). */
export function TypingIndicator({ children }: { children: ReactNode }) {
  return (
    <div
      className="mr-auto inline-flex max-w-[85%] items-center gap-3 rounded-bubble rounded-bl-md border border-line bg-canvas px-4 py-3 text-sm text-muted"
      role="status"
    >
      <span className="flex items-center gap-1" aria-hidden="true">
        <span className="typing-dot" />
        <span className="typing-dot [animation-delay:150ms]" />
        <span className="typing-dot [animation-delay:300ms]" />
      </span>
      {children}
    </div>
  );
}

/** Centered empty-state copy for chat logs and lists. */
export function EmptyNote({ children }: { children: ReactNode }) {
  return (
    <div className="flex min-h-[9rem] flex-1 flex-col items-center justify-center px-4 py-8 text-center">
      <p className="max-w-xs text-sm leading-relaxed text-muted">{children}</p>
    </div>
  );
}
