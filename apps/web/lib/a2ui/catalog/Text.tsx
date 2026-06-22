"use client";

import { CatalogComponentProps } from "../Renderer";
import { resolveValue } from "../resolve";

export function TextComp({ node, ctx }: CatalogComponentProps) {
  const raw = resolveValue(node.text, ctx.state.dataModel, ctx.scope);
  const variant = typeof node.variant === "string" ? node.variant : "body";

  const isNumber =
    typeof raw === "number" ||
    (typeof raw === "string" && raw.trim() !== "" && !Number.isNaN(Number(raw)));

  const text = raw == null ? "" : String(raw);

  // A numeric score is rendered as a telemetry readout regardless of variant
  // (unless it is the divine headline itself).
  if (isNumber && variant !== "h1") {
    return (
      <span className="a2-text a2-text--score" data-score>
        {text}
      </span>
    );
  }

  const cls =
    variant === "h1"
      ? "a2-text a2-text--h1"
      : variant === "h2"
        ? "a2-text a2-text--h2"
        : variant === "caption"
          ? "a2-text a2-text--caption"
          : "a2-text a2-text--body";

  if (variant === "h1") return <h1 className={cls}>{text}</h1>;
  if (variant === "h2") return <h2 className={cls}>{text}</h2>;
  return <p className={cls}>{text}</p>;
}
