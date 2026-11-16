import ReactMarkdown from "react-markdown";
import remarkMath from "remark-math";
import rehypeKatex from "rehype-katex";

const block = (m: string) => "\n$$\n" + m.trim() + "\n$$\n";

/**
 * Models sometimes emit \( \) / \[ \] delimiters, or put $$…$$ on one line;
 * remark-math only understands $ / $$, and only treats $$ as display maths
 * when the fences sit on their own lines.
 */
export function normaliseMath(src: string): string {
  return src
    .replace(/\\\[([\s\S]+?)\\\]/g, (_, m: string) => block(m))
    .replace(/\\\(([\s\S]+?)\\\)/g, (_, m: string) => "$" + m + "$")
    .replace(/^[ \t]*\$\$([^\n]+?)\$\$[ \t]*$/gm, (_, m: string) => block(m));
}

export default function Markdown({ children }: { children: string }) {
  return (
    <div className="prose-tutor min-w-0 break-words leading-relaxed">
      <ReactMarkdown
        remarkPlugins={[remarkMath]}
        rehypePlugins={[[rehypeKatex, { throwOnError: false, strict: "ignore" }]]}
        components={{
          // eslint-disable-next-line @typescript-eslint/no-unused-vars
          a: ({ node, ...props }) => (
            <a {...props} target="_blank" rel="noopener noreferrer" className="text-accent underline" />
          ),
        }}
      >
        {normaliseMath(children)}
      </ReactMarkdown>
    </div>
  );
}
