import { useLayoutEffect, useRef, useState } from "react";

interface Option<T extends string> {
  value: T;
  label: string;
}

/**
 * Segmented control: options sit in one soft tray and a raised highlight
 * slides to the selected one. Works when the options wrap onto two rows
 * (phones), because the highlight is measured in both axes.
 */
export default function Segmented<T extends string>({
  options,
  value,
  onChange,
  label,
  className = "",
}: {
  options: readonly Option<T>[];
  value: T;
  onChange: (value: T) => void;
  /** Accessible name for the group. */
  label: string;
  /** Layout classes for the tray, e.g. grid columns and width. */
  className?: string;
}) {
  const trayRef = useRef<HTMLDivElement>(null);
  const itemRefs = useRef<Partial<Record<T, HTMLButtonElement | null>>>({});
  const [box, setBox] = useState({ x: 0, y: 0, w: 0, h: 0, ready: false });

  useLayoutEffect(() => {
    const measure = () => {
      const item = itemRefs.current[value];
      if (item) {
        setBox({
          x: item.offsetLeft,
          y: item.offsetTop,
          w: item.offsetWidth,
          h: item.offsetHeight,
          ready: true,
        });
      }
    };
    measure();
    const tray = trayRef.current;
    if (!tray || typeof ResizeObserver === "undefined") return;
    const observer = new ResizeObserver(measure);
    observer.observe(tray);
    return () => observer.disconnect();
  }, [value]);

  return (
    <div
      ref={trayRef}
      role="group"
      aria-label={label}
      className={"segmented-tray " + className}
    >
      <span
        aria-hidden="true"
        className="segmented-glide"
        style={{
          transform: `translate(${box.x}px, ${box.y}px)`,
          width: box.w,
          height: box.h,
          opacity: box.ready ? 1 : 0,
        }}
      />
      {options.map((option) => {
        const active = option.value === value;
        return (
          <button
            key={option.value}
            ref={(node) => {
              itemRefs.current[option.value] = node;
            }}
            type="button"
            onClick={() => onChange(option.value)}
            aria-pressed={active}
            className={"segmented-item " + (active ? "segmented-item-on" : "segmented-item-off")}
          >
            {option.label}
          </button>
        );
      })}
    </div>
  );
}
