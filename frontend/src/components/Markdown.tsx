import ReactMarkdown, { type Components } from "react-markdown";
import remarkGfm from "remark-gfm";

/**
 * Renders model output (notes, answers, summaries) as formatted Markdown:
 * headings, lists, tables, emphasis, code and quotes, styled to the app.
 * Raw HTML in the source is not rendered.
 *
 * `size="doc"` is for long-form reading (notes); `size="chat"` is compact
 * for message bubbles.
 */
export default function Markdown({
  children,
  size = "chat",
}: {
  children: string;
  size?: "doc" | "chat";
}) {
  const doc = size === "doc";

  const components: Components = {
    h1: ({ children }) => (
      <h1
        className={
          "font-semibold tracking-[-0.02em] text-ink first:mt-0 " +
          (doc ? "mb-4 mt-8 text-2xl leading-8" : "mb-2 mt-4 text-base leading-6")
        }
      >
        {children}
      </h1>
    ),
    h2: ({ children }) => (
      <h2
        className={
          "font-semibold tracking-[-0.015em] text-ink first:mt-0 " +
          (doc
            ? "mb-3 mt-8 border-b border-line pb-2 text-lg leading-7"
            : "mb-2 mt-4 text-[15px] leading-6")
        }
      >
        {children}
      </h2>
    ),
    h3: ({ children }) => (
      <h3
        className={
          "font-semibold text-ink first:mt-0 " +
          (doc ? "mb-2 mt-6 text-base leading-6" : "mb-1 mt-3 text-sm leading-6")
        }
      >
        {children}
      </h3>
    ),
    h4: ({ children }) => (
      <h4 className="mb-1 mt-4 text-sm font-semibold leading-6 text-ink-soft first:mt-0">
        {children}
      </h4>
    ),
    p: ({ children }) => <p className={doc ? "my-3 first:mt-0 last:mb-0" : "my-2 first:mt-0 last:mb-0"}>{children}</p>,
    ul: ({ children }) => (
      <ul className="my-3 list-disc space-y-1 pl-5 marker:text-accent first:mt-0 last:mb-0">
        {children}
      </ul>
    ),
    ol: ({ children }) => (
      <ol className="my-3 list-decimal space-y-1 pl-5 marker:font-medium marker:text-muted first:mt-0 last:mb-0">
        {children}
      </ol>
    ),
    li: ({ children }) => <li className="pl-1">{children}</li>,
    strong: ({ children }) => <strong className="font-semibold text-ink">{children}</strong>,
    em: ({ children }) => <em className="italic">{children}</em>,
    a: ({ href, children }) => (
      <a href={href} target="_blank" rel="noopener noreferrer" className="link">
        {children}
      </a>
    ),
    blockquote: ({ children }) => (
      <blockquote className="my-4 rounded-r-control border-l-[3px] border-accent bg-accent-soft py-2 pl-4 pr-3 text-ink-soft">
        {children}
      </blockquote>
    ),
    hr: () => <hr className="my-6 border-line" />,
    code: ({ className, children }) => {
      const block = /language-/.test(className ?? "") || String(children).includes("\n");
      return block ? (
        <code className="block font-mono text-[13px] leading-6">{children}</code>
      ) : (
        <code className="rounded-md border border-line bg-sunken px-1.5 py-0.5 font-mono text-[0.85em] text-accent-ink">
          {children}
        </code>
      );
    },
    pre: ({ children }) => (
      <pre className="my-4 overflow-x-auto rounded-panel border border-line bg-sunken px-4 py-3 text-ink">
        {children}
      </pre>
    ),
    table: ({ children }) => (
      <div className="my-4 overflow-x-auto rounded-panel border border-line">
        <table className="w-full border-collapse text-left text-sm">{children}</table>
      </div>
    ),
    thead: ({ children }) => <thead className="bg-accent-soft">{children}</thead>,
    th: ({ children }) => (
      <th className="whitespace-nowrap border-b border-accent-line px-3 py-2 text-[13px] font-semibold text-accent-ink">
        {children}
      </th>
    ),
    tr: ({ children }) => <tr className="even:bg-canvas">{children}</tr>,
    td: ({ children }) => (
      <td className="border-b border-line px-3 py-2 align-top leading-6 text-ink-soft">{children}</td>
    ),
  };

  return (
    <div
      className={
        "min-w-0 break-words text-ink [&_tr:last-child_td]:border-b-0 " +
        (doc ? "text-[15px] leading-7" : "text-sm leading-6")
      }
    >
      <ReactMarkdown remarkPlugins={[remarkGfm]} components={components}>
        {children}
      </ReactMarkdown>
    </div>
  );
}
