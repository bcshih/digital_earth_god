function tokens(path: string): string[] {
  if (path === "" || path === "/") return [];
  return path
    .replace(/^\//, "")
    .split("/")
    .map((t) => t.replace(/~1/g, "/").replace(/~0/g, "~"));
}

export function getAtPointer(root: unknown, path: string): unknown {
  let cur: unknown = root;
  for (const t of tokens(path)) {
    if (cur == null) return undefined;
    if (Array.isArray(cur)) cur = cur[Number(t)];
    else cur = (cur as Record<string, unknown>)[t];
  }
  return cur;
}

export function setAtPointer(
  root: Record<string, unknown>,
  path: string,
  value: unknown,
): Record<string, unknown> {
  const ts = tokens(path);
  if (ts.length === 0) return (value as Record<string, unknown>) ?? {};
  const next = structuredClone(root);
  let cur: Record<string, unknown> | unknown[] = next;
  for (let i = 0; i < ts.length - 1; i++) {
    const key = ts[i];
    const nextKey = ts[i + 1];
    const childWantsArray = /^\d+$/.test(nextKey);
    if (Array.isArray(cur)) {
      const idx = Number(key);
      if (cur[idx] == null) cur[idx] = childWantsArray ? [] : {};
      cur = cur[idx] as Record<string, unknown> | unknown[];
    } else {
      if (cur[key] == null) cur[key] = childWantsArray ? [] : {};
      cur = cur[key] as Record<string, unknown> | unknown[];
    }
  }
  const last = ts[ts.length - 1];
  if (Array.isArray(cur)) cur[Number(last)] = value;
  else (cur as Record<string, unknown>)[last] = value;
  return next;
}
