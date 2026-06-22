"use client";

import { CatalogComponentProps } from "../Renderer";
import { resolveValue } from "../resolve";

// A small glyph registry mapping common semantic names to a divine sigil.
const GLYPHS: Record<string, string> = {
  incense: "🕯",
  temple: "⛩",
  star: "✦",
  spark: "✶",
  check: "✓",
  location: "◉",
  scroll: "𓏏",
};

export function IconComp({ node, ctx }: CatalogComponentProps) {
  const name = resolveValue(node.name ?? node.icon, ctx.state.dataModel, ctx.scope);
  const key = typeof name === "string" ? name : "";
  const glyph = GLYPHS[key] ?? "✦";
  return (
    <span className="a2-icon" role="img" aria-label={key || "icon"}>
      {glyph}
    </span>
  );
}
