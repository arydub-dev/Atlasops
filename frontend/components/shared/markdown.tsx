import { Fragment } from "react";

/** Minimal, dependency-free markdown renderer for AI responses
 *  (supports #/##/### headings, - bullets, 1. lists, **bold**, `code`). */
export function Markdown({ content }: { content: string }) {
  const lines = content.split("\n");
  const blocks: React.ReactNode[] = [];
  let list: { ordered: boolean; items: string[] } | null = null;

  const flush = () => {
    if (!list) return;
    const items = list.items.map((t, i) => <li key={i}>{inline(t)}</li>);
    blocks.push(
      list.ordered ? (
        <ol key={blocks.length} className="ml-5 list-decimal space-y-1">{items}</ol>
      ) : (
        <ul key={blocks.length} className="ml-5 list-disc space-y-1">{items}</ul>
      )
    );
    list = null;
  };

  for (const raw of lines) {
    const line = raw.trimEnd();
    if (!line.trim()) {
      flush();
      continue;
    }
    if (line.startsWith("### ")) {
      flush();
      blocks.push(<h4 key={blocks.length} className="mt-3 text-sm font-semibold">{inline(line.slice(4))}</h4>);
    } else if (line.startsWith("## ")) {
      flush();
      blocks.push(<h3 key={blocks.length} className="mt-3 text-base font-semibold">{inline(line.slice(3))}</h3>);
    } else if (line.startsWith("# ")) {
      flush();
      blocks.push(<h2 key={blocks.length} className="text-lg font-semibold">{inline(line.slice(2))}</h2>);
    } else if (/^\d+\.\s/.test(line)) {
      if (!list || !list.ordered) {
        flush();
        list = { ordered: true, items: [] };
      }
      list.items.push(line.replace(/^\d+\.\s/, ""));
    } else if (line.startsWith("- ") || line.startsWith("* ")) {
      if (!list || list.ordered) {
        flush();
        list = { ordered: false, items: [] };
      }
      list.items.push(line.slice(2));
    } else {
      flush();
      blocks.push(<p key={blocks.length} className="text-sm leading-relaxed">{inline(line)}</p>);
    }
  }
  flush();

  return <div className="space-y-2">{blocks}</div>;
}

function inline(text: string): React.ReactNode {
  const parts = text.split(/(\*\*[^*]+\*\*|`[^`]+`|_[^_]+_)/g);
  return parts.map((p, i) => {
    if (p.startsWith("**") && p.endsWith("**"))
      return <strong key={i} className="font-semibold">{p.slice(2, -2)}</strong>;
    if (p.startsWith("`") && p.endsWith("`"))
      return <code key={i} className="rounded bg-muted px-1 py-0.5 font-mono text-xs">{p.slice(1, -1)}</code>;
    if (p.startsWith("_") && p.endsWith("_"))
      return <em key={i} className="text-muted-foreground">{p.slice(1, -1)}</em>;
    return <Fragment key={i}>{p}</Fragment>;
  });
}
