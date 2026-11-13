import { useEffect, useRef } from "react";

/** Nearest ancestor that scrolls vertically, or null. */
function scrollParent(node: HTMLElement | null): HTMLElement | null {
  let current = node?.parentElement ?? null;
  while (current) {
    const { overflowY } = window.getComputedStyle(current);
    if (overflowY === "auto" || overflowY === "scroll") return current;
    current = current.parentElement;
  }
  return null;
}

/**
 * Keeps a chat log pinned to its newest message whenever `deps` change.
 *
 * Attach the returned ref to a sentinel at the bottom of the log. Only the
 * log's own scroll container moves, never the page, so the frozen header
 * and the rest of the screen stay put while messages arrive.
 */
export function useChatScroll(deps: unknown[]): React.RefObject<HTMLDivElement> {
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const container = scrollParent(endRef.current);
    if (container && typeof container.scrollTo === "function") {
      container.scrollTo({ top: container.scrollHeight, behavior: "smooth" });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);

  return endRef;
}
