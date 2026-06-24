"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Renderer, EventContext, Decorator } from "@/lib/a2ui/Renderer";
import { applyMessage, emptySurface } from "@/lib/a2ui/store";
import { getAtPointer, setAtPointer } from "@/lib/a2ui/pointer";
import { SurfaceState, A2uiMessage } from "@/lib/a2ui/types";
import { IncenseBackground } from "@/components/theater/IncenseBackground";
import { TempleNav } from "@/components/TempleNav";
import {
  CouncilMap,
  CouncilBoundary,
  CouncilStatementRow,
  CouncilAlignmentRow,
} from "@/components/CouncilMap";

const WS_URL =
  process.env.NEXT_PUBLIC_GATEWAY_WS_COUNCIL ??
  "ws://127.0.0.1:8080/ws/council/a2ui";

type Conn =
  | "connecting"
  | "open"
  | "routing"
  | "assembling"
  | "done"
  | "error"
  | "failed";

export default function CouncilPage() {
  const [state, setState] = useState<SurfaceState>(emptySurface);
  const [conn, setConn] = useState<Conn>("connecting");
  const [errorDetail, setErrorDetail] = useState<string | null>(null);

  const wsRef = useRef<WebSocket | null>(null);
  const stateRef = useRef<SurfaceState>(state);
  const terminalRef = useRef(false);

  useEffect(() => {
    stateRef.current = state;
  }, [state]);

  useEffect(() => {
    let ws: WebSocket;
    try {
      ws = new WebSocket(WS_URL);
    } catch {
      const t = setTimeout(() => setConn("failed"), 0);
      return () => clearTimeout(t);
    }
    wsRef.current = ws;

    ws.onopen = () => setConn((c) => (c === "connecting" ? "open" : c));

    ws.onmessage = (ev) => {
      let msg: A2uiMessage;
      try {
        msg = JSON.parse(ev.data as string) as A2uiMessage;
      } catch {
        return;
      }
      if ("a2uiDone" in msg) {
        terminalRef.current = true;
        setConn("done");
        return;
      }
      if ("a2uiError" in msg) {
        terminalRef.current = true;
        setErrorDetail((msg as { a2uiError: string }).a2uiError);
        setConn("error");
        return;
      }
      if ("a2uiPhase" in msg) {
        const phase = (msg as { a2uiPhase: string }).a2uiPhase;
        if (phase === "routing") setConn("routing");
        if (phase === "assembling") setConn("assembling");
        return;
      }
      setState((prev) => applyMessage(prev, msg));
    };

    ws.onerror = () => {
      if (!terminalRef.current) setConn((c) => (c === "done" ? c : "failed"));
    };
    ws.onclose = () => {
      if (terminalRef.current) return;
      setConn((c) =>
        c === "done" || c === "error" || c === "assembling" || c === "open"
          ? c
          : "failed",
      );
    };

    return () => {
      terminalRef.current = true;
      try {
        ws.close();
      } catch {
        /* noop */
      }
      wsRef.current = null;
    };
  }, []);

  const onEvent = useCallback(async (name: string, context: EventContext) => {
    const ws = wsRef.current;
    if (!ws || ws.readyState !== WebSocket.OPEN) return;

    if (name === "submit_council") {
      const fromCtx = typeof context.topic === "string" ? context.topic : null;
      const fromModel = getAtPointer(stateRef.current.dataModel, "/council/topic");
      const topic =
        (fromCtx ?? (typeof fromModel === "string" ? fromModel : "")) || "";
      if (!topic.trim()) return;
      ws.send(JSON.stringify({ topic }));
      setConn("routing");
    }
  }, []);

  const onDataModelChange = useCallback((path: string, value: unknown) => {
    setState((prev) => ({
      ...prev,
      dataModel: setAtPointer(prev.dataModel, path, value),
    }));
  }, []);

  // Pull the live map inputs out of the data model.
  const boundaries = useMemo<CouncilBoundary[]>(() => {
    const b = getAtPointer(state.dataModel, "/boundaries");
    return Array.isArray(b) ? (b as CouncilBoundary[]) : [];
  }, [state.dataModel]);

  const statements = useMemo<CouncilStatementRow[]>(() => {
    const s = getAtPointer(state.dataModel, "/statements");
    return Array.isArray(s) ? (s.filter(Boolean) as CouncilStatementRow[]) : [];
  }, [state.dataModel]);

  const alignments = useMemo<CouncilAlignmentRow[]>(() => {
    const a = getAtPointer(state.dataModel, "/council/alignments");
    return Array.isArray(a) ? (a as CouncilAlignmentRow[]) : [];
  }, [state.dataModel]);

  // agent_id → street_name lookup for the "responds_to" display
  const nameById = useMemo(
    () => new Map(boundaries.map((b) => [b.agent_id, b.street_name])),
    [boundaries],
  );

  const STANCE_LABEL: Record<string, string> = {
    support: "附議",
    oppose: "反駁",
    question: "提問",
    inform: "補充",
  };

  // Mount the Leaflet council map in place of the `council-map` placeholder,
  // and replace statement-card with a compact inline row.
  const decorate = useCallback<Decorator>(
    ({ id, scope }) => {
      if (id === "council-map" && boundaries.length > 0) {
        return (
          <div key="council-map-shell" className="council-map-shell">
            <span className="council-map-shell__kicker">里長大會 · 神界輿圖</span>
            <CouncilMap
              boundaries={boundaries}
              statements={statements}
              alignments={alignments}
            />
            <CouncilLegend />
          </div>
        );
      }
      if (id === "statement-card") {
        const idx = parseInt(scope.replace("/statements/", ""), 10);
        const stmt = !isNaN(idx) ? statements[idx] : undefined;
        if (!stmt || stmt.stance === "silent") return null;
        const respondName = stmt.responds_to ? nameById.get(stmt.responds_to) : null;
        return (
          <div key={`stmt-${idx}`} className="stmt-row">
            <span className={`stmt-name stmt-name--${stmt.stance}`}>{stmt.street_name}</span>
            <span className={`stmt-badge stmt-badge--${stmt.stance}`}>
              {STANCE_LABEL[stmt.stance] ?? stmt.stance}
            </span>
            {respondName && <span className="stmt-responds">→ {respondName}</span>}
            <span className="stmt-text">{stmt.statement_text}</span>
          </div>
        );
      }
      return null;
    },
    [boundaries, statements, alignments, nameById],
  );

  const offline = conn === "failed";

  return (
    <IncenseBackground>
      <main className="sanctum">
        <TempleNav active="council" />

        <div className="sanctum__brand">
          <span className="sanctum__seal">會</span>
          <span className="sanctum__kicker">COUNCIL · 里長大會 (live)</span>
        </div>

        <div className="live-status">
          <span className="live-status__dot" data-conn={conn} />
          <span className="live-status__label">{statusLabel(conn)}</span>
        </div>

        {conn === "error" && (
          <div style={{ marginTop: "0.6rem" }}>
            {errorDetail && (
              <p
                className="a2-text a2-text--caption"
                style={{
                  color: "var(--color-error, #f87171)",
                  marginBottom: "0.8rem",
                }}
              >
                {errorDetail}
              </p>
            )}
            <button
              className="a2-button a2-button--primary"
              onClick={() => window.location.reload()}
            >
              重新連接
            </button>
          </div>
        )}

        {offline ? (
          <div className="temple-closed" role="alert">
            <div className="temple-closed__seal">闭</div>
            <h2 className="temple-closed__title">土地公廟暫時關閉</h2>
            <p className="temple-closed__body">
              請先啟動 gateway（
              <code>uvicorn apps.api.gateway:app</code>）。
            </p>
          </div>
        ) : (
          <Renderer
            state={state}
            onEvent={onEvent}
            onDataModelChange={onDataModelChange}
            decorate={decorate}
          />
        )}

        {!offline && conn === "connecting" && state.surfaceId === null && (
          <p
            className="a2-text a2-text--caption"
            style={{ marginTop: "1.6rem" }}
          >
            正在連接土地公廟…
          </p>
        )}
      </main>
    </IncenseBackground>
  );
}

function CouncilLegend() {
  const items: { label: string; cls: string }[] = [
    { label: "發言中", cls: "speaking" },
    { label: "支持", cls: "support" },
    { label: "反駁", cls: "oppose" },
    { label: "提問", cls: "question" },
    { label: "補充", cls: "inform" },
  ];
  return (
    <div className="council-legend" aria-hidden>
      {items.map((it) => (
        <span key={it.cls} className="council-legend__item">
          <span className={`council-legend__dot council-legend__dot--${it.cls}`} />
          {it.label}
        </span>
      ))}
    </div>
  );
}

function statusLabel(conn: Conn): string {
  switch (conn) {
    case "connecting":
      return "連接中…";
    case "open":
      return "土地公已臨壇 · 請出題";
    case "routing":
      return "各地神明正在到場…";
    case "assembling":
      return "里長大會進行中…";
    case "done":
      return "土地公裁示已下";
    case "error":
      return "大會中斷";
    case "failed":
      return "廟門深鎖";
  }
}
