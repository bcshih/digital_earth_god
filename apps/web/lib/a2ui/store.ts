import { A2uiMessage, Component, SurfaceState, emptySurface } from "./types";
import { setAtPointer } from "./pointer";

export function applyMessage(state: SurfaceState, msg: A2uiMessage): SurfaceState {
  if ("createSurface" in msg) {
    return {
      surfaceId: msg.createSurface.surfaceId,
      catalogId: msg.createSurface.catalogId,
      components: {},
      dataModel: {},
    };
  }
  if ("updateComponents" in msg) {
    const components = { ...state.components };
    for (const c of msg.updateComponents.components as Component[]) components[c.id] = c;
    return { ...state, components };
  }
  if ("updateDataModel" in msg) {
    const { path, value } = msg.updateDataModel;
    return { ...state, dataModel: setAtPointer(state.dataModel, path || "/", value) };
  }
  return state; // a2uiDone / a2uiError: no state change
}

export { emptySurface };
