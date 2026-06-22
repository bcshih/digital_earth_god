import { isBinding } from "./types";
import { getAtPointer } from "./pointer";

/** Resolve a prop value: Binding -> dataModel lookup (absolute or template-relative); else literal. */
export function resolveValue(value: unknown, dataModel: unknown, scope: string): unknown {
  if (isBinding(value)) {
    const p = value.path;
    const full = p.startsWith("/") ? p : `${scope}/${p}`;
    return getAtPointer(dataModel, full);
  }
  return value;
}
