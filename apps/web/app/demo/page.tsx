"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { Renderer, EventContext } from "@/lib/a2ui/Renderer";
import { applyMessage, emptySurface } from "@/lib/a2ui/store";
import { setAtPointer } from "@/lib/a2ui/pointer";
import { SurfaceState } from "@/lib/a2ui/types";
import { exploreDemo } from "@/lib/transcript/exploreDemo";

type Status = "idle" | "playing" | "done" | "error";
type LogLine = { idx: number; kind: string; detail: string; terminal?: "done" | "error" };

function describe(msg: (typeof exploreDemo)[number]): { kind: string; detail: string; terminal?: "done" | "error" } {
  if ("createSurface" in msg) {
    return { kind: "createSurface", detail: `surface=${msg.createSurface.surfaceId}` };
  }
  if ("updateComponents" in msg) {
    const ids = msg.updateComponents.components.map((c) => c.id);
    return { kind: "updateComponents", detail: `${ids.length} components` };
  }
  if ("updateDataModel" in msg) {
    return { kind: "updateDataModel", detail: msg.updateDataModel.path };
  }
  if ("a2uiDone" in msg) return { kind: "a2uiDone", detail: "terminal", terminal: "done" };
  return { kind: "a2uiError", detail: (msg as { a2uiError: string }).a2uiError, terminal: "error" };
}

// Pace: ~700-1100ms per frame; a longer hush before the verdict updateComponents.
function delayFor(idx: number): number {
  const msg = exploreDemo[idx];
  if ("updateComponents" in msg && msg.updateComponents.components[0]?.id === "verdict-card") {
    return 1600; // the擲筊 pause
  }
  if ("updateDataModel" in msg && msg.updateDataModel.path?.startsWith("/bids/")) {
    return 900; // each bid arrives with weight
  }
  return 800;
}

export default function DemoPage() {
  const [state, setState] = useState<SurfaceState>(emptySurface);
  const [status, setStatus] = useState<Status>("playing");
  const [log, setLog] = useState<LogLine[]>([]);
  const [runId, setRunId] = useState(0);
  const timers = useRef<ReturnType<typeof setTimeout>[]>([]);

  const clearTimers = () => {
    timers.current.forEach(clearTimeout);
    timers.current = [];
  };

  // Schedule the replay. The effect only sets state asynchronously (inside
  // timers), never synchronously in the effect body — re-running is driven by
  // runId, and the reset lives in the replay() handler below.
  useEffect(() => {
    clearTimers();
    let acc = 0;
    let live = emptySurface();

    exploreDemo.forEach((msg, idx) => {
      acc += idx === 0 ? 300 : delayFor(idx - 1);
      const t = setTimeout(() => {
        live = applyMessage(live, msg);
        setState(live);
        const d = describe(msg);
        setLog((prev) => [...prev, { idx, ...d }]);
        if (d.terminal === "done") setStatus("done");
        if (d.terminal === "error") setStatus("error");
      }, acc);
      timers.current.push(t);
    });

    return clearTimers;
  }, [runId]);

  const replay = useCallback(() => {
    clearTimers();
    setState(emptySurface());
    setLog([]);
    setStatus("playing");
    setRunId((n) => n + 1);
  }, []);

  const onEvent = useCallback((name: string, context: EventContext) => {
    // In the offline demo the transcript drives the surface; we just log intent.
    setLog((prev) => [
      ...prev,
      { idx: -1, kind: `event:${name}`, detail: JSON.stringify(context) },
    ]);
  }, []);

  const onDataModelChange = useCallback((path: string, value: unknown) => {
    setState((prev) => ({
      ...prev,
      dataModel: setAtPointer(prev.dataModel, path, value),
    }));
  }, []);

  return (
    <main className="sanctum">
      <div className="sanctum__brand">
        <span className="sanctum__seal">土</span>
        <span className="sanctum__kicker">EXPLORE · 招標展演 (offline transcript)</span>
      </div>

      <div className="demo-replay">
        <span className="demo-replay__status">
          <span className="demo-replay__pulse" data-done={status !== "playing"} />
          {status === "playing"
            ? "土地公作法中…"
            : status === "done"
              ? "擲筊三聖 · 裁決已下"
              : status === "error"
                ? "作法中斷"
                : "待命"}
        </span>
        <Link className="demo-replay__btn" href="/" style={{ textDecoration: "none" }}>
          ← 回到山門
        </Link>
        <button className="demo-replay__btn" onClick={replay}>
          ↻ 重新擲筊
        </button>
      </div>

      <Renderer state={state} onEvent={onEvent} onDataModelChange={onDataModelChange} />

      <div className="ritual-log" aria-live="polite">
        {log.slice(-7).map((l, i) => (
          <div className="ritual-log__line" key={`${l.idx}-${l.kind}-${i}`}>
            <span className="ritual-log__tick">
              {l.idx >= 0 ? String(l.idx).padStart(2, "0") : "··"}
            </span>
            <span
              className={
                l.terminal === "done"
                  ? "ritual-log__done"
                  : l.terminal === "error"
                    ? "ritual-log__err"
                    : ""
              }
            >
              {l.kind}
            </span>
            <span className="ritual-log__msg">{l.detail}</span>
          </div>
        ))}
      </div>
    </main>
  );
}
