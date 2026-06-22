"use client";

import { CatalogComponentProps } from "../Renderer";

export function CardComp({ node, ctx }: CatalogComponentProps) {
  const child = typeof node.child === "string" ? node.child : null;
  return (
    <section className="a2-card">
      <span className="a2-card__corner a2-card__corner--tl" aria-hidden />
      <span className="a2-card__corner a2-card__corner--tr" aria-hidden />
      <span className="a2-card__corner a2-card__corner--bl" aria-hidden />
      <span className="a2-card__corner a2-card__corner--br" aria-hidden />
      <div className="a2-card__body">
        {child ? ctx.render(child, ctx.scope) : null}
      </div>
    </section>
  );
}
