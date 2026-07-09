import { useEffect, useRef } from "react";

/**
 * Scrolls a sentinel element into view whenever any of the given dependencies
 * change. Returns a ref that must be attached to a sentinel element placed at
 * the bottom of the scroll container.
 *
 * Usage:
 *   const endRef = useChatScroll([messages, busy]);
 *   …
 *   <div ref={endRef} />
 */
export function useChatScroll(deps: unknown[]): React.RefObject<HTMLDivElement> {
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView?.({ behavior: "smooth" });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);

  return endRef;
}
