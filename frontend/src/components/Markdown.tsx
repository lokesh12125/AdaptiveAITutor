import ReactMarkdown from "react-markdown";

/** Renders problem and hint text. Raw HTML is not allowed, so imported text cannot inject markup. */
export function Markdown({ children }: { children: string }) {
  return (
    <div className="markdown">
      <ReactMarkdown skipHtml>{children}</ReactMarkdown>
    </div>
  );
}
