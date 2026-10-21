"use client";

/**
 * A small Markdown renderer for generated text.
 *
 * The model writes Markdown, and showing a user the Markdown source — a wall
 * of `###`, `**` and pipe tables — is not a rendering of an answer, it is a
 * rendering of the answer's plumbing. So it is rendered.
 *
 * It is rendered *safely*, which is the whole point of doing it here rather
 * than reaching for a Markdown library:
 *
 * - **No HTML is ever produced.** The parser returns React elements, so
 *   everything is escaped by React itself. There is no
 *   `dangerouslySetInnerHTML` anywhere, which is also what the repository's
 *   compliance check requires.
 * - **Only a known subset is understood** — headings, bold, italic, inline
 *   code, fenced code, links, lists and tables. Anything else is left as the
 *   text it is.
 * - **Only `http` and `https` links are linked.** A `javascript:` URL in
 *   generated text is text.
 *
 * The subset is deliberately small. A renderer that tries to be a Markdown
 * implementation is a renderer with a large attack surface, and the thing
 * being rendered is a career suggestion, not a README.
 */
import * as React from "react";

import { cn } from "@/lib/utils";

type Inline = React.ReactNode;

interface Block {
  kind: "heading" | "paragraph" | "list" | "table" | "code" | "rule";
  level?: number;
  ordered?: boolean;
  items?: string[];
  rows?: string[][];
  header?: boolean;
  lines?: string[];
  text?: string;
}

const INLINE_PATTERN =
  /(\*\*[^*]+\*\*|__[^_]+__|\*[^*\n]+\*|_[^_\n]+_|`[^`\n]+`|\[[^\]\n]+\]\([^)\s]+\))/;

/** Split a line into React nodes, interpreting the inline subset. */
function renderInline(text: string, keyPrefix: string): Inline[] {
  const nodes: Inline[] = [];
  let rest = text;

  while (rest.length > 0) {
    const match = INLINE_PATTERN.exec(rest);
    if (!match || match.index === undefined) {
      nodes.push(rest);
      break;
    }
    if (match.index > 0) {
      nodes.push(rest.slice(0, match.index));
    }
    const token = match[0];
    const key = `${keyPrefix}-${nodes.length}`;

    if (token.startsWith("**") || token.startsWith("__")) {
      nodes.push(
        <strong key={key} className="font-semibold text-foreground">
          {token.slice(2, -2)}
        </strong>,
      );
    } else if (token.startsWith("`")) {
      nodes.push(
        <code
          key={key}
          className="rounded bg-muted px-1 py-0.5 font-mono text-[0.85em]"
        >
          {token.slice(1, -1)}
        </code>,
      );
    } else if (token.startsWith("[")) {
      const linkMatch = /^\[([^\]\n]+)\]\(([^)\s]+)\)$/.exec(token);
      const label = linkMatch?.[1] ?? token;
      const href = linkMatch?.[2] ?? "";
      if (/^https?:\/\//i.test(href)) {
        nodes.push(
          <a
            key={key}
            href={href}
            target="_blank"
            rel="noreferrer noopener"
            className="font-medium text-primary underline underline-offset-4"
          >
            {label}
          </a>,
        );
      } else {
        // Not a link we are willing to follow. Show the text.
        nodes.push(label);
      }
    } else {
      nodes.push(
        <em key={key} className="italic">
          {token.slice(1, -1)}
        </em>,
      );
    }

    rest = rest.slice(match.index + token.length);
  }

  return nodes;
}

const HEADING = /^(#{1,6})\s+(.*)$/;
const UNORDERED = /^\s*[-*+]\s+(.*)$/;
const ORDERED = /^\s*(\d+)[.)]\s+(.*)$/;
const TABLE_ROW = /^\s*\|(.+)\|\s*$/;
const TABLE_SEPARATOR = /^\s*\|[\s:|-]+\|\s*$/;
const FENCE = /^\s*```/;

/** Turn a block of text into a list of blocks. */
function parseBlocks(source: string): Block[] {
  const lines = source.replace(/\r\n/g, "\n").split("\n");
  const blocks: Block[] = [];
  let index = 0;

  while (index < lines.length) {
    const line = lines[index];

    if (!line.trim()) {
      index += 1;
      continue;
    }

    if (FENCE.test(line)) {
      const body: string[] = [];
      index += 1;
      while (index < lines.length && !FENCE.test(lines[index])) {
        body.push(lines[index]);
        index += 1;
      }
      index += 1; // the closing fence
      blocks.push({ kind: "code", lines: body });
      continue;
    }

    if (/^\s*(---|\*\*\*|___)\s*$/.test(line)) {
      blocks.push({ kind: "rule" });
      index += 1;
      continue;
    }

    const heading = HEADING.exec(line);
    if (heading) {
      blocks.push({
        kind: "heading",
        level: heading[1].length,
        text: heading[2].trim(),
      });
      index += 1;
      continue;
    }

    if (TABLE_ROW.test(line)) {
      const rows: string[][] = [];
      while (index < lines.length && TABLE_ROW.test(lines[index])) {
        if (!TABLE_SEPARATOR.test(lines[index])) {
          rows.push(
            lines[index]
              .replace(TABLE_ROW, "$1")
              .split("|")
              .map((cell) => cell.trim()),
          );
        }
        index += 1;
      }
      if (rows.length > 0) {
        blocks.push({ kind: "table", rows, header: true });
      }
      continue;
    }

    if (UNORDERED.test(line)) {
      const items: string[] = [];
      while (index < lines.length && UNORDERED.test(lines[index])) {
        items.push(UNORDERED.exec(lines[index])?.[1] ?? "");
        index += 1;
      }
      blocks.push({ kind: "list", items, ordered: false });
      continue;
    }

    if (ORDERED.test(line)) {
      const items: string[] = [];
      while (index < lines.length && ORDERED.test(lines[index])) {
        items.push(ORDERED.exec(lines[index])?.[2] ?? "");
        index += 1;
      }
      blocks.push({ kind: "list", items, ordered: true });
      continue;
    }

    // A paragraph: consecutive non-blank lines that are not something else.
    const paragraph: string[] = [];
    while (
      index < lines.length &&
      lines[index].trim() &&
      !HEADING.test(lines[index]) &&
      !UNORDERED.test(lines[index]) &&
      !ORDERED.test(lines[index]) &&
      !TABLE_ROW.test(lines[index]) &&
      !FENCE.test(lines[index])
    ) {
      paragraph.push(lines[index].trim());
      index += 1;
    }
    if (paragraph.length > 0) {
      blocks.push({ kind: "paragraph", text: paragraph.join(" ") });
    }
  }

  return blocks;
}

interface MarkdownTextProps {
  text: string;
  className?: string;
}

export function MarkdownText({ text, className }: MarkdownTextProps) {
  const blocks = React.useMemo(() => parseBlocks(text ?? ""), [text]);

  return (
    <div className={cn("space-y-3 text-sm leading-relaxed", className)}>
      {blocks.map((block, index) => {
        const key = `b${index}`;
        switch (block.kind) {
          case "heading": {
            const size =
              block.level && block.level <= 2
                ? "text-base font-semibold"
                : "text-sm font-semibold";
            return (
              <p key={key} className={cn(size, "text-foreground")}>
                {renderInline(block.text ?? "", key)}
              </p>
            );
          }
          case "list": {
            const ListTag = block.ordered ? "ol" : "ul";
            return (
              <ListTag
                key={key}
                className={cn(
                  "space-y-1 pl-5",
                  block.ordered ? "list-decimal" : "list-disc",
                )}
              >
                {(block.items ?? []).map((item, itemIndex) => (
                  <li key={`${key}-${itemIndex}`}>
                    {renderInline(item, `${key}-${itemIndex}`)}
                  </li>
                ))}
              </ListTag>
            );
          }
          case "table": {
            const rows = block.rows ?? [];
            const [header, ...body] = rows;
            return (
              <div key={key} className="overflow-x-auto rounded-md border">
                <table className="w-full text-left text-xs">
                  {block.header && header ? (
                    <thead className="border-b bg-muted/50">
                      <tr>
                        {header.map((cell, cellIndex) => (
                          <th key={`${key}-h${cellIndex}`} className="px-3 py-2 font-semibold">
                            {renderInline(cell, `${key}-h${cellIndex}`)}
                          </th>
                        ))}
                      </tr>
                    </thead>
                  ) : null}
                  <tbody>
                    {body.map((row, rowIndex) => (
                      <tr key={`${key}-r${rowIndex}`} className="border-b last:border-b-0">
                        {row.map((cell, cellIndex) => (
                          <td key={`${key}-r${rowIndex}c${cellIndex}`} className="px-3 py-2 align-top">
                            {renderInline(cell, `${key}-r${rowIndex}c${cellIndex}`)}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            );
          }
          case "code":
            return (
              <pre
                key={key}
                className="overflow-x-auto rounded-md bg-muted p-3 font-mono text-xs"
              >
                <code>{(block.lines ?? []).join("\n")}</code>
              </pre>
            );
          case "rule":
            return <hr key={key} className="border-border" />;
          default:
            return (
              <p key={key} className="whitespace-pre-wrap">
                {renderInline(block.text ?? "", key)}
              </p>
            );
        }
      })}
    </div>
  );
}
