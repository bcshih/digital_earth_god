"use client";

import { CatalogComponentProps } from "../Renderer";

export function Column({ node, ctx }: CatalogComponentProps) {
  const children = Array.isArray(node.children) ? (node.children as string[]) : [];
  return (
    <div className="a2-column">
      {children.map((childId) => ctx.render(childId, ctx.scope))}
    </div>
  );
}
