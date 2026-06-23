"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { Renderer, EventContext, Decorator } from "@/lib/a2ui/Renderer";
import { applyMessage, emptySurface } from "@/lib/a2ui/store";
import { getAtPointer, setAtPointer } from "@/lib/a2ui/pointer";
import { SurfaceState, A2uiMessage } from "@/lib/a2ui/types";
import { IncenseBackground } from "@/components/theater/IncenseBackground";
import { TempleNav } from "@/components/TempleNav";
import { ChatBubble } from "@/components/ChatBubble";

const WS_URL =
  process.env.NEXT_PUBLIC_GATEWAY_WS_COMMUNITY ??
  "ws://127.0.0.1:8080/ws/ask/a2ui";

type Conn =
  | "connecting"
  | "open"
  | "routing"
  | "answering"
  | "done"
  | "error"
  | "failed";

export default function AskPage() {
  const [state, setState] = useState<SurfaceState>(emptySurface);
  const [conn, setConn] = useState<Conn>("connecting");
  const [errorDetail, setErrorDetail] = useState<string | null>(null);
  const [chatOpen, setChatOpen] = useState(false);

  const wsRef = useRef<WebSocket | null>(null);
  const stateRef = useRef<SurfaceState>(state);
  const terminalRef = useRef(false);

  useEffect(() => {
    stateRef.current = state;
  }, [state]);

  useEffect(() => {
    if (conn === "routing" || conn === "answering") {
      setChatOpen(true);
    }
  }, [conn]);

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
        if (phase === "answering") setConn("answering");
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
        c === "done" || c === "error" || c === "answering" || c === "open"
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

    if (name === "submit_community") {
      const fromCtx = typeof context.question === "string" ? context.question : null;
      const fromModel = getAtPointer(stateRef.current.dataModel, "/community/question");
      const question =
        (fromCtx ?? (typeof fromModel === "string" ? fromModel : "")) || "";
      if (!question.trim()) return;
      ws.send(JSON.stringify({ question }));
      setConn("routing");
    }
  }, []);

  const onDataModelChange = useCallback((path: string, value: unknown) => {
    setState((prev) => ({
      ...prev,
      dataModel: setAtPointer(prev.dataModel, path, value),
    }));
  }, []);

  const decorate = useCallback<Decorator>(
    ({ id, scope, element }) => {
      if (id === "scout-card") {
        return <ChatBubble key={`scout@${scope}`}>{element}</ChatBubble>;
      }
      if (id === "scouts-row") {
        return (
          <>
            {chatOpen && (
              <div className="chat-backdrop" onClick={() => setChatOpen(false)} />
            )}
            <button
              className="chat-toggle"
              onClick={() => setChatOpen((v) => !v)}
              aria-label={chatOpen ? "關閉對話" : "查看里神對話"}
            >
              {chatOpen ? "✕" : "💬"}
            </button>
            <div key={`scout-room@${scope}`} className={`chat-room${chatOpen ? " chat-room--open" : ""}`}>
              {element}
            </div>
          </>
        );
      }
      return null;
    },
    [chatOpen],
  );

  const offline = conn === "failed";

  return (
    <IncenseBackground>
      <main className="sanctum">
        <TempleNav active="ask" />

        <div className="sanctum__brand">
          <span className="sanctum__seal">問</span>
          <span className="sanctum__kicker">ASK · 問土地公社區大小事</span>
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

function statusLabel(conn: Conn): string {
  switch (conn) {
    case "connecting":
      return "連接中…";
    case "open":
      return "土地公已臨壇 · 請叩問";
    case "routing":
      return "各地神明正在評估…";
    case "answering":
      return "地基主們回報中…";
    case "done":
      return "土地公神諭已下";
    case "error":
      return "問法中斷";
    case "failed":
      return "廟門深鎖";
  }
}
