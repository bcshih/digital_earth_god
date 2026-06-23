"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import { Renderer, EventContext, Decorator } from "@/lib/a2ui/Renderer";
import { applyMessage, emptySurface } from "@/lib/a2ui/store";
import { setAtPointer, getAtPointer } from "@/lib/a2ui/pointer";
import { SurfaceState, A2uiMessage } from "@/lib/a2ui/types";
import { IncenseBackground } from "@/components/theater/IncenseBackground";
import { SealStamp } from "@/components/theater/SealStamp";
import { Jiaobei } from "@/components/theater/Jiaobei";
import { ResultMap, MapItineraryStop } from "@/components/ResultMap";
import { TempleNav } from "@/components/TempleNav";
import { ChatBubble } from "@/components/ChatBubble";
import { NegotiationBoard } from "@/components/NegotiationBoard";

const WS_URL =
  process.env.NEXT_PUBLIC_GATEWAY_WS ?? "ws://127.0.0.1:8080/ws/explore/a2ui";

// Earthly seat of the sanctum, used when device geolocation is unavailable.
const DEFAULT_LAT = 22.9971;
const DEFAULT_LNG = 120.201;

type Conn = "connecting" | "open" | "clarifying" | "submitted" | "retrying" | "done" | "error" | "failed";

// Persist the completed TaskBroadcast across a manual reconnect so the user
// doesn't have to answer the 五營兵將 questions again. Session-scoped (per tab).
const RESUME_TOKEN_KEY = "deg.resumeBroadcast";
const RESUME_FLAG_KEY = "deg.doResume";

function getLatLng(): Promise<{ lat: number; lng: number }> {
  return new Promise((resolve) => {
    if (typeof navigator === "undefined" || !navigator.geolocation) {
      resolve({ lat: DEFAULT_LAT, lng: DEFAULT_LNG });
      return;
    }
    navigator.geolocation.getCurrentPosition(
      (pos) => resolve({ lat: pos.coords.latitude, lng: pos.coords.longitude }),
      () => resolve({ lat: DEFAULT_LAT, lng: DEFAULT_LNG }),
      { timeout: 4000, maximumAge: 600000 },
    );
  });
}

export default function Home() {
  const [state, setState] = useState<SurfaceState>(emptySurface);
  const [conn, setConn] = useState<Conn>("connecting");
  const [errorDetail, setErrorDetail] = useState<string | null>(null);
  const [chatOpen, setChatOpen] = useState(false);

  const wsRef = useRef<WebSocket | null>(null);
  const stateRef = useRef<SurfaceState>(state);
  // Guards a stale onclose from flipping a deliberately-finished socket to "failed".
  const terminalRef = useRef(false);

  // Keep the latest surface in a ref for the onEvent handler (mounts once).
  useEffect(() => {
    stateRef.current = state;
  }, [state]);

  // Auto-open chat drawer on mobile when agents start responding.
  useEffect(() => {
    if (conn === "submitted" || conn === "retrying") {
      setChatOpen(true);
    }
  }, [conn]);

  useEffect(() => {
    let ws: WebSocket;
    try {
      ws = new WebSocket(WS_URL);
    } catch {
      // Defer to avoid a synchronous setState inside the effect body.
      const t = setTimeout(() => setConn("failed"), 0);
      return () => clearTimeout(t);
    }
    wsRef.current = ws;

    ws.onopen = () => {
      setConn((c) => (c === "connecting" ? "open" : c));
      // Resume path: if the user hit 重新連接, replay the cached broadcast so the
      // server skips clarification and goes straight back to bidding.
      try {
        if (sessionStorage.getItem(RESUME_FLAG_KEY) === "1") {
          const cached = sessionStorage.getItem(RESUME_TOKEN_KEY);
          if (cached) {
            ws.send(JSON.stringify({ task_broadcast: JSON.parse(cached) }));
            setConn("submitted");
          }
          sessionStorage.removeItem(RESUME_FLAG_KEY); // one-shot
        }
      } catch {
        /* sessionStorage unavailable — fall back to fresh flow */
      }
    };

    ws.onmessage = (ev) => {
      let msg: A2uiMessage;
      try {
        msg = JSON.parse(ev.data as string) as A2uiMessage;
      } catch {
        return; // ignore non-JSON frames
      }
      if ("a2uiDone" in msg) {
        terminalRef.current = true;
        try {
          sessionStorage.removeItem(RESUME_TOKEN_KEY);
          sessionStorage.removeItem(RESUME_FLAG_KEY);
        } catch {
          /* noop */
        }
        setConn("done");
        return;
      }
      if ("a2uiError" in msg) {
        terminalRef.current = true;
        setErrorDetail((msg as { a2uiError: string }).a2uiError);
        setConn("error");
        return;
      }
      // Resume token: cache the full broadcast for a possible reconnect.
      if ("a2uiResumeToken" in msg) {
        try {
          const tok = (msg as { a2uiResumeToken: unknown }).a2uiResumeToken;
          sessionStorage.setItem(RESUME_TOKEN_KEY, JSON.stringify(tok));
        } catch {
          /* noop */
        }
        return;
      }
      // Phase signals from the gateway (non-A2UI control frames)
      if ("a2uiPhase" in msg) {
        const phase = (msg as { a2uiPhase: string }).a2uiPhase;
        if (phase === "clarifying") setConn("clarifying");
        if (phase === "negotiating") setConn("submitted");
        if (phase === "retrying") setConn("retrying");
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
        c === "done" || c === "error" || c === "submitted" || c === "open" ? c : "failed",
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

  // The user submitted the sealed intent button → send the one client→server msg.
  const onEvent = useCallback(async (name: string, context: EventContext) => {
    const ws = wsRef.current;
    if (!ws || ws.readyState !== WebSocket.OPEN) return;

    if (name === "submit_intent") {
      const fromCtx = typeof context.text === "string" ? context.text : null;
      const fromModel = getAtPointer(stateRef.current.dataModel, "/intent/text");
      const intentText = (fromCtx ?? (typeof fromModel === "string" ? fromModel : "")) || "";
      if (!intentText.trim()) return;
      const { lat, lng } = await getLatLng();
      ws.send(JSON.stringify({ intent_text: intentText, lat, lng }));
      setConn("submitted"); // immediate feedback; server a2uiPhase may override to "clarifying"
    } else if (name === "submit_clarify") {
      const fromCtx = typeof context.answer === "string" ? context.answer : null;
      const fromModel = getAtPointer(stateRef.current.dataModel, "/clarify/answer");
      const answerText = (fromCtx ?? (typeof fromModel === "string" ? fromModel : "")) || "";
      ws.send(JSON.stringify({ answer_text: answerText }));
      setConn("submitted"); // immediate feedback; server a2uiPhase may override to "clarifying"
    }
  }, []);

  // TextField writeback → keep the local data model in sync before submit.
  const onDataModelChange = useCallback((path: string, value: unknown) => {
    setState((prev) => ({
      ...prev,
      dataModel: setAtPointer(prev.dataModel, path, value),
    }));
  }, []);

  // Has the verdict data actually arrived? (Distinguishes the filled verdict
  // card from the skeleton placeholder so 擲筊 only plays on the real verdict.)
  const verdict = getAtPointer(state.dataModel, "/verdict") as
    | { itinerary?: MapItineraryStop[] }
    | undefined;
  const verdictReady = !!verdict && typeof verdict === "object";
  const itinerary = useMemo<MapItineraryStop[]>(() => {
    const arr = verdict?.itinerary;
    return Array.isArray(arr) ? arr : [];
  }, [verdict]);

  // Group by day for the map
  const itineraryByDay = useMemo(() => {
    if (!itinerary.length) return [];
    const grouped = new Map<number, MapItineraryStop[]>();
    for (const stop of itinerary) {
      const d = stop.day || 1;
      if (!grouped.has(d)) grouped.set(d, []);
      grouped.get(d)!.push(stop);
    }
    return Array.from(grouped.entries()).sort((a, b) => a[0] - b[0]);
  }, [itinerary]);

  // The domain-agnostic decoration hook handed to the generic Renderer. It only
  // layers presentation onto two well-known ids; everything else passes through.
  const decorate = useCallback<Decorator>(
    ({ id, scope, element }) => {
      if (id === "negotiation-board") {
        const bids = Array.isArray(state?.dataModel?.bids) ? state.dataModel.bids : [];
        const debates = Array.isArray(state?.dataModel?.debates) ? state.dataModel.debates : [];
        return <NegotiationBoard key="negotiation-board" bids={bids} debates={debates} />;
      }
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
      // The verdict: gate behind 擲筊, then append the Leaflet result map.
      if (id === "verdict-card" && verdictReady) {
        return (
          <Jiaobei key="jiaobei">
            {element}
            {itineraryByDay.map(([day, stops]) => (
              <div key={`map-day-${day}`} className="verdict-map-shell">
                <span className="verdict-map-shell__kicker">神界輿圖 · 第 {day} 天</span>
                <ResultMap itinerary={stops} />
              </div>
            ))}
          </Jiaobei>
        );
      }
      return null;
    },
    [verdictReady, itineraryByDay, state, chatOpen],
  );

  const offline = conn === "failed";

  return (
    <IncenseBackground>
      <main className="sanctum">
        <TempleNav active="explore" />

        <div className="sanctum__brand">
          <span className="sanctum__seal">土</span>
          <span className="sanctum__kicker">EXPLORE · 五營兵將招標 (live)</span>
        </div>

        <div className="live-status">
          <span className="live-status__dot" data-conn={conn} />
          <span className="live-status__label">{statusLabel(conn)}</span>
          <Link className="live-status__link" href="/demo">
            觀禮展演 /demo →
          </Link>
        </div>

        {conn === "error" ? (
          <div style={{ marginTop: "0.6rem" }}>
            {errorDetail ? (
              <p className="a2-text a2-text--caption" style={{ color: "var(--color-error, #f87171)", wordBreak: "break-all", marginBottom: "0.8rem" }}>
                {errorDetail}
              </p>
            ) : null}
            <button
              className="a2-button a2-button--primary"
              onClick={() => {
                // Arm resume so the reload skips clarification if we already
                // have a completed broadcast cached.
                try {
                  if (sessionStorage.getItem(RESUME_TOKEN_KEY)) {
                    sessionStorage.setItem(RESUME_FLAG_KEY, "1");
                  }
                } catch {
                  /* noop */
                }
                window.location.reload();
              }}
            >
              重新連接
            </button>
          </div>
        ) : null}

        {offline ? (
          <div className="temple-closed" role="alert">
            <div className="temple-closed__seal">闭</div>
            <h2 className="temple-closed__title">土地公廟暫時關閉</h2>
            <p className="temple-closed__body">
              請先啟動 gateway（
              <code>uvicorn apps.api.gateway:app</code>），或前往{" "}
              <Link href="/demo" className="temple-closed__link">
                /demo
              </Link>{" "}
              觀禮。
            </p>
            {errorDetail ? (
              <p className="temple-closed__detail">{errorDetail}</p>
            ) : null}
          </div>
        ) : (
          <Renderer
            state={state}
            onEvent={onEvent}
            onDataModelChange={onDataModelChange}
            decorate={decorate}
          />
        )}

        {!offline && conn === "connecting" && state.surfaceId === null ? (
          <p className="a2-text a2-text--caption" style={{ marginTop: "1.6rem" }}>
            正在連接土地公廟…
          </p>
        ) : null}
      </main>
    </IncenseBackground>
  );
}

function statusLabel(conn: Conn): string {
  switch (conn) {
    case "connecting":
      return "連接中…";
    case "open":
      return "土地公已臨壇 · 待稟報";
    case "clarifying":
      return "五營兵將正在追問…";
    case "submitted":
      return "招標令已發 · 地基主競標中…";
    case "retrying":
      return "香火過旺 · 稍候片刻再請神…";
    case "done":
      return "擲筊三聖 · 裁決已下";
    case "error":
      return "作法中斷";
    case "failed":
      return "廟門深鎖";
  }
}
