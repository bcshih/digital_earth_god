"use client";

import { CatalogComponentProps } from "../Renderer";
import { resolveValue } from "../resolve";

export function ImageComp({ node, ctx }: CatalogComponentProps) {
  const src = resolveValue(node.src ?? node.url, ctx.state.dataModel, ctx.scope);
  const alt = resolveValue(node.alt, ctx.state.dataModel, ctx.scope);
  if (typeof src !== "string" || src === "") {
    return <div className="a2-image a2-image--empty" aria-hidden />;
  }
  return (
    // A2UI Image src is an arbitrary runtime URL from the stream; next/image's
    // build-time domain config does not apply, so a plain <img> is correct here.
    // eslint-disable-next-line @next/next/no-img-element
    <img className="a2-image" src={src} alt={typeof alt === "string" ? alt : ""} />
  );
}
