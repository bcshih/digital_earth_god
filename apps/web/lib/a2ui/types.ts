export type Binding = { path: string };
export type PropValue = unknown; // literal | Binding | nested
export type Component = {
  id: string;
  component: string;
  [key: string]: unknown;
};
export type TemplateChildren = { path: string; componentId: string };
export type A2uiMessage =
  | { version: string; createSurface: { surfaceId: string; catalogId: string; sendDataModel?: boolean } }
  | { version: string; updateComponents: { surfaceId: string; components: Component[] } }
  | { version: string; updateDataModel: { surfaceId: string; path: string; value: unknown } }
  | { a2uiDone: true }
  | { a2uiError: string };

export type SurfaceState = {
  surfaceId: string | null;
  catalogId: string | null;
  components: Record<string, Component>;
  dataModel: Record<string, unknown>;
};

export function emptySurface(): SurfaceState {
  return { surfaceId: null, catalogId: null, components: {}, dataModel: {} };
}

export function isBinding(v: unknown): v is Binding {
  return (
    typeof v === "object" &&
    v !== null &&
    "path" in (v as object) &&
    typeof (v as Binding).path === "string"
  );
}
export function isTemplateChildren(v: unknown): v is TemplateChildren {
  return typeof v === "object" && v !== null && "componentId" in (v as object);
}
