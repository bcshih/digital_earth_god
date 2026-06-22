"use client";

import { FC } from "react";
import { Component, SurfaceState, isTemplateChildren } from "./types";
import { CATALOG } from "./catalog";

export type EventContext = Record<string, unknown>;

/**
 * Optional, domain-agnostic decoration hook. The generic renderer calls this for
 * every component instance, passing the component's id, the active data scope and
 * the resolved node, plus the already-rendered element. A host (e.g. the live
 * page) can return a wrapped element to layer presentation-only behaviour — ritual
 * animations, reveals — onto specific ids WITHOUT the core renderer knowing any
 * domain semantics. Returning `null`/`undefined` (or omitting the prop entirely)
 * leaves the element untouched. Children remain id strings; unknown components
 * still fall back. The swappable-renderer contract is preserved: this is a pure
 * post-render wrapper, never a replacement for catalog resolution.
 */
export type Decorator = (args: {
  id: string;
  scope: string;
  node: Component;
  element: React.ReactNode;
}) => React.ReactNode;

export type RenderContext = {
  state: SurfaceState;
  scope: string;
  onEvent: (name: string, context: EventContext) => void;
  onDataModelChange: (path: string, value: unknown) => void;
  render: (id: string, scope: string) => React.ReactNode;
};

export type CatalogComponentProps = {
  node: Component;
  ctx: RenderContext;
};

/**
 * Determine the render root: the component with id "root" if present, else the
 * single component that is not referenced by any other component's child/children.
 */
function findRootId(components: Record<string, Component>): string | null {
  if (components["root"]) return "root";
  const ids = Object.keys(components);
  if (ids.length === 0) return null;
  const referenced = new Set<string>();
  for (const c of Object.values(components)) {
    const child = c.child;
    if (typeof child === "string") referenced.add(child);
    const children = c.children;
    if (Array.isArray(children)) {
      for (const ch of children) if (typeof ch === "string") referenced.add(ch);
    } else if (isTemplateChildren(children)) {
      referenced.add(children.componentId);
    }
  }
  const roots = ids.filter((id) => !referenced.has(id));
  return roots[0] ?? ids[0];
}

export function Renderer({
  state,
  onEvent,
  onDataModelChange,
  decorate,
}: {
  state: SurfaceState;
  onEvent: (name: string, context: EventContext) => void;
  onDataModelChange: (path: string, value: unknown) => void;
  decorate?: Decorator;
}) {
  const rootId = findRootId(state.components);
  if (!rootId) return null;

  const render = (id: string, scope: string): React.ReactNode => {
    const node = state.components[id];
    if (!node) {
      return <FallbackBox key={id} label={`missing:${id}`} />;
    }
    const Comp: FC<CatalogComponentProps> | undefined = CATALOG[node.component];
    const ctx: RenderContext = { state, scope, onEvent, onDataModelChange, render };
    if (!Comp) {
      return <FallbackBox key={id} label={`unknown:${node.component} (${id})`} />;
    }
    const element = <Comp key={`${id}@${scope}`} node={node} ctx={ctx} />;
    // Optional host decoration: a pure post-render wrapper. The decorator is
    // responsible for preserving the key when it wraps the element.
    if (decorate) {
      const wrapped = decorate({ id, scope, node, element });
      if (wrapped != null) return wrapped;
    }
    return element;
  };

  return <>{render(rootId, "")}</>;
}

function FallbackBox({ label }: { label: string }) {
  return (
    <div
      style={{
        border: "1px dashed var(--seal)",
        color: "var(--seal)",
        fontFamily: "var(--font-mono)",
        fontSize: 11,
        padding: "6px 10px",
        borderRadius: 4,
        opacity: 0.7,
      }}
    >
      ⟂ {label}
    </div>
  );
}
