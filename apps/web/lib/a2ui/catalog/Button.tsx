"use client";

import { CatalogComponentProps } from "../Renderer";
import { resolveValue } from "../resolve";

type Check = {
  condition?: { call?: string; args?: { value?: unknown } };
  message?: string;
};

type ActionEvent = {
  event?: { name?: string; context?: Record<string, unknown> };
};

function isEmpty(v: unknown): boolean {
  if (v == null) return true;
  if (typeof v === "string") return v.trim() === "";
  if (Array.isArray(v)) return v.length === 0;
  return false;
}

export function ButtonComp({ node, ctx }: CatalogComponentProps) {
  const child = typeof node.child === "string" ? node.child : null;

  // Evaluate checks: a failed "required" check disables the button + shows message.
  const checks = Array.isArray(node.checks) ? (node.checks as Check[]) : [];
  let failMessage: string | null = null;
  for (const chk of checks) {
    if (chk.condition?.call === "required") {
      const val = resolveValue(chk.condition.args?.value, ctx.state.dataModel, ctx.scope);
      if (isEmpty(val)) {
        failMessage = chk.message ?? "必填";
        break;
      }
    }
  }
  const disabled = failMessage !== null;

  const action = node.action as ActionEvent | undefined;
  const eventName = action?.event?.name;

  function handleClick() {
    if (disabled || !eventName) return;
    const rawCtx = action?.event?.context ?? {};
    const resolved: Record<string, unknown> = {};
    for (const [k, v] of Object.entries(rawCtx)) {
      resolved[k] = resolveValue(v, ctx.state.dataModel, ctx.scope);
    }
    ctx.onEvent(eventName, resolved);
  }

  return (
    <div className="a2-button-wrap">
      <button
        type="button"
        className="a2-button a2-button--primary"
        disabled={disabled}
        onClick={handleClick}
      >
        <span className="a2-button__glow" aria-hidden />
        <span className="a2-button__label">
          {child ? ctx.render(child, ctx.scope) : null}
        </span>
      </button>
      {failMessage ? <span className="a2-button__hint">{failMessage}</span> : null}
    </div>
  );
}
