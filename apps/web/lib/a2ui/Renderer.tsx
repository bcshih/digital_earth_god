"use client";

import { FC } from "react";
import { Component, SurfaceState, isTemplateChildren } from "./types";
import { CATALOG } from "./catalog";

export type EventContext = Record<string, unknown>;
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
}: {
  state: SurfaceState;
  onEvent: (name: string, context: EventContext) => void;
  onDataModelChange: (path: string, value: unknown) => void;
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
    return <Comp key={`${id}@${scope}`} node={node} ctx={ctx} />;
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
