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
import { ResultMap, MapPoi } from "@/components/ResultMap";
import { TempleNav } from "@/components/TempleNav";

const WS_URL =
  process.env.NEXT_PUBLIC_GATEWAY_WS ?? "ws://127.0.0.1:8080/ws/explore/a2ui";

// Earthly seat of the sanctum, used when device geolocation is unavailable.
const DEFAULT_LAT = 22.9971;
const DEFAULT_LNG = 120.201;

type Conn = "connecting" | "open" | "clarifying" | "submitted" | "done" | "error" | "failed";

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

  const wsRef = useRef<WebSocket | null>(null);
  const stateRef = useRef<SurfaceState>(state);
  // Guards a stale onclose from flipping a deliberately-finished socket to "failed".
  const terminalRef = useRef(false);

  // Keep the latest surface in a ref for the onEvent handler (mounts once).
  useEffect(() => {
    stateRef.current = state;
  }, [state]);

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

    ws.onopen = () => setConn((c) => (c === "connecting" ? "open" : c));

    ws.onmessage = (ev) => {
      let msg: A2uiMessage;
      try {
        msg = JSON.parse(ev.data as string) as A2uiMessage;
      } catch {
        return; // ignore non-JSON frames
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
      // Phase signals from the gateway (non-A2UI control frames)
      if ("a2uiPhase" in msg) {
        const phase = (msg as { a2uiPhase: string }).a2uiPhase;
        if (phase === "clarifying") setConn("clarifying");
        if (phase === "negotiating") setConn("submitted");
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
    | { recommended_pois?: MapPoi[] }
    | undefined;
  const verdictReady = !!verdict && typeof verdict === "object";
  const recommendedPois = useMemo<MapPoi[]>(() => {
    const arr = verdict?.recommended_pois;
    return Array.isArray(arr) ? arr : [];
  }, [verdict]);

  // The domain-agnostic decoration hook handed to the generic Renderer. It only
  // layers presentation onto two well-known ids; everything else passes through.
  const decorate = useCallback<Decorator>(
    ({ id, scope, element }) => {
      // 地基主 bid cards: stamp each in like a vermillion seal, staggered by index.
      if (id === "bid-card") {
        const m = scope.match(/\/bids\/(\d+)$/);
        const index = m ? Number(m[1]) : 0;
        return (
          <SealStamp key={`seal@${scope}`} index={index}>
            {element}
          </SealStamp>
        );
      }
      // The verdict: gate behind 擲筊, then append the Leaflet result map.
      if (id === "verdict-card" && verdictReady) {
        return (
          <Jiaobei key="jiaobei">
            {element}
            {recommendedPois.length > 0 ? (
              <div className="verdict-map-shell">
                <span className="verdict-map-shell__kicker">神界輿圖 · RECOMMENDED</span>
                <ResultMap pois={recommendedPois} />
              </div>
            ) : null}
          </Jiaobei>
        );
      }
      return null;
    },
    [verdictReady, recommendedPois],
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
              onClick={() => window.location.reload()}
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
    case "done":
      return "擲筊三聖 · 裁決已下";
    case "error":
      return "作法中斷";
    case "failed":
      return "廟門深鎖";
  }
}
