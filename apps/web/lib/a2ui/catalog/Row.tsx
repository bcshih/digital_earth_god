"use client";

import { CatalogComponentProps } from "../Renderer";

export function Row({ node, ctx }: CatalogComponentProps) {
  const children = Array.isArray(node.children) ? (node.children as string[]) : [];
  return (
    <div className="a2-row">
      {children.map((childId) => ctx.render(childId, ctx.scope))}
    </div>
  );
}
