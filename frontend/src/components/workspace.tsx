import type { ReactNode } from "react";

/**
 * Page skeleton used by every signed-in screen.
 *
 *   ┌ PageHeader ─────────────────────────────┐  frozen, never scrolls
 *   │ Title / one-line description / tabs     │
 *   ├ PageBody ───────────────────────────────┤  the only scrolling region
 *   │ Workspace: [ aside | main pane ]        │
 *   └─────────────────────────────────────────┘
 *
 * Header and body share one gutter + max width so every edge lines up.
 */

const FRAME = "mx-auto w-full max-w-page px-4 sm:px-6 lg:px-8";

export function PageHeader({
  title,
  description,
  actions,
  children,
}: {
  title: ReactNode;
  description?: ReactNode;
  actions?: ReactNode;
  /** Optional row under the title, e.g. tabs. */
  children?: ReactNode;
}) {
  return (
    <header className="shrink-0 border-b border-line bg-gradient-to-b from-white to-[#FFFCF9]">
      <div className={FRAME}>
        <div className={"flex items-center justify-between gap-4 " + (children ? "pt-5" : "py-5")}>
          <div className="min-w-0">
            <h1 className="truncate text-xl font-semibold leading-8 tracking-[-0.02em] text-ink">
              {title}
            </h1>
            {description && (
              <p className="mt-0.5 hidden truncate text-sm text-muted sm:block">{description}</p>
            )}
          </div>
          {actions && <div className="flex shrink-0 items-center gap-2">{actions}</div>}
        </div>
        {children && <div className="mt-3 pb-3">{children}</div>}
      </div>
    </header>
  );
}

/**
 * Scrolling content region under the frozen header.
 * `fill` makes the body exactly fill the remaining height on desktop so a
 * workspace can keep its chat composer pinned without the page scrolling.
 */
export function PageBody({ children, fill = false }: { children: ReactNode; fill?: boolean }) {
  return (
    <div
      className={
        "min-h-0 flex-1 overflow-y-auto overscroll-contain " + (fill ? "lg:overflow-hidden" : "")
      }
    >
      <div className={FRAME + " py-6 " + (fill ? "lg:h-full" : "pb-12")}>{children}</div>
    </div>
  );
}

/** Two-pane layout: controls on the left, the working surface on the right. */
export function Workspace({ aside, children }: { aside: ReactNode; children: ReactNode }) {
  return (
    <div className="grid gap-6 lg:h-full lg:grid-cols-[minmax(0,21rem)_minmax(0,1fr)]">
      {/* Children never shrink: a card with overflow-hidden would otherwise be
          squashed to the leftover height and clip its content. The aside
          scrolls as a whole instead. */}
      <aside className="no-scrollbar flex min-w-0 flex-col gap-3 lg:min-h-0 lg:overflow-y-auto lg:pb-1 [&>*]:shrink-0">
        {aside}
      </aside>
      <section className="flex h-[min(42rem,calc(100dvh-8rem))] min-h-[26rem] min-w-0 flex-col lg:h-auto lg:min-h-0">
        {children}
      </section>
    </div>
  );
}

/** Small titled card used inside a workspace aside. */
export function AsideCard({
  title,
  children,
  className = "",
}: {
  title?: ReactNode;
  children: ReactNode;
  className?: string;
}) {
  return (
    <div className={"card p-4 " + className}>
      {title && <h2 className="section-title mb-2.5">{title}</h2>}
      {children}
    </div>
  );
}
