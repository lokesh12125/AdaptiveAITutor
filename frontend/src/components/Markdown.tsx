import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

/** Renders problem, hint and lesson text. Raw HTML is not allowed, so imported text cannot inject markup. */
export function Markdown({ children, className }: { children: string; className?: string }) {
  return (
    <div className={`markdown ${className ?? ""}`}>
      <ReactMarkdown skipHtml remarkPlugins={[remarkGfm]}>{children}</ReactMarkdown>
    </div>
  );
}

/** Short text whose `code` spans show as code, for places that allow only inline content, such as a form label. */
export function InlineCode({ text }: { text: string }) {
  return <>{text.split(/(`[^`]+`)/g).map((part, i) => (part.length > 2 && part.startsWith("`") && part.endsWith("`") ? <code key={i}>{part.slice(1, -1)}</code> : part))}</>;
}
