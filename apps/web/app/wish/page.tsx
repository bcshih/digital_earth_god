"use client";

import { Suspense, useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Renderer, EventContext, Decorator } from "@/lib/a2ui/Renderer";
import { applyMessage, emptySurface } from "@/lib/a2ui/store";
import { setAtPointer, getAtPointer } from "@/lib/a2ui/pointer";
import { SurfaceState, A2uiMessage } from "@/lib/a2ui/types";
import { IncenseBackground } from "@/components/theater/IncenseBackground";
import { BlessingBloom } from "@/components/theater/BlessingBloom";
import { WishLocationPicker } from "@/components/WishLocationPicker";
import { TempleNav } from "@/components/TempleNav";
import { wishDemo } from "@/lib/transcript/wishDemo";

const WS_BASE =
  process.env.NEXT_PUBLIC_GATEWAY_WS ?? "ws://127.0.0.1:8080/ws/explore/a2ui";
// Reuse the explore host but swap the path to the wish socket.
const WISH_WS_URL = WS_BASE.replace(/\/ws\/[^/]+\/a2ui$/, "/ws/wish/a2ui");

// Earthly seat of the sanctum, used when device geolocation is unavailable.
const DEFAULT_LAT = 22.9971;
const DEFAULT_LNG = 120.201;

type Conn = "connecting" | "open" | "submitted" | "done" | "error" | "failed";

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

// Does the blessing surface data exist yet? Gates the bloom so it only plays
// on the real blessing, not the input form.
function blessingReady(state: SurfaceState): boolean {
  const b = getAtPointer(state.dataModel, "/blessing");
  return !!b && typeof b === "object";
}

function statusLabel(conn: Conn): string {
  switch (conn) {
    case "connecting":
      return "連接中…";
    case "open":
      return "土地公已臨壇 · 請上香許願";
    case "submitted":
      return "香火已上 · 土地公聆聽中…";
    case "done":
      return "祝福已賜 · 心願收下";
    case "error":
      return "作法中斷";
    case "failed":
      return "廟門深鎖";
  }
}

// ── Live mode: real WebSocket to the gateway ─────────────────────────────────
function WishLive() {
  const [state, setState] = useState<SurfaceState>(emptySurface);
  const [conn, setConn] = useState<Conn>("connecting");
  const [errorDetail, setErrorDetail] = useState<string | null>(null);

  const wsRef = useRef<WebSocket | null>(null);
  const stateRef = useRef<SurfaceState>(state);
  const terminalRef = useRef(false);
  const pickerLatRef = useRef<number>(DEFAULT_LAT);
  const pickerLngRef = useRef<number>(DEFAULT_LNG);
  const [pickerLat, setPickerLat] = useState<number>(DEFAULT_LAT);
  const [pickerLng, setPickerLng] = useState<number>(DEFAULT_LNG);
  const locationReady = useRef(false);

  useEffect(() => {
    stateRef.current = state;
  }, [state]);

  useEffect(() => {
    let ws: WebSocket;
    try {
      ws = new WebSocket(WISH_WS_URL);
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

  useEffect(() => {
    if (locationReady.current) return;
    locationReady.current = true;
    getLatLng().then(({ lat, lng }) => {
      setPickerLat(lat);
      setPickerLng(lng);
      pickerLatRef.current = lat;
      pickerLngRef.current = lng;
    });
  }, []);

  const onEvent = useCallback((name: string, context: EventContext) => {
    if (name !== "submit_wish") return;
    const fromCtx = typeof context.text === "string" ? context.text : null;
    const fromModel = getAtPointer(stateRef.current.dataModel, "/wish/text");
    const wishText = (fromCtx ?? (typeof fromModel === "string" ? fromModel : "")) || "";
    if (!wishText.trim()) return;

    const ws = wsRef.current;
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ wish_text: wishText, lat: pickerLatRef.current, lng: pickerLngRef.current }));
      setConn("submitted");
    }
  }, []);

  const onDataModelChange = useCallback((path: string, value: unknown) => {
    setState((prev) => ({
      ...prev,
      dataModel: setAtPointer(prev.dataModel, path, value),
    }));
  }, []);

  const ready = blessingReady(state);
  const decorate = useCallback<Decorator>(
    ({ id, element }) => {
      // Wrap the blessing card in a gentle golden bloom once its data arrives.
      if (id === "blessing-card" && ready) {
        return <BlessingBloom key="blessing-bloom">{element}</BlessingBloom>;
      }
      return null;
    },
    [ready],
  );

  const offline = conn === "failed";

  return (
    <WishShell mode="live" conn={conn}>
      {offline ? (
        <div className="temple-closed" role="alert">
          <div className="temple-closed__seal">闭</div>
          <h2 className="temple-closed__title">土地公廟暫時關閉</h2>
          <p className="temple-closed__body">
            請先啟動 gateway（
            <code>uvicorn apps.api.gateway:app</code>），或前往{" "}
            <Link href="/wish?demo=1" className="temple-closed__link">
              /wish?demo=1
            </Link>{" "}
            觀禮，亦可至{" "}
            <Link href="/demo" className="temple-closed__link">
              /demo
            </Link>
            。
          </p>
          {errorDetail ? (
            <p className="temple-closed__detail">{errorDetail}</p>
          ) : null}
        </div>
      ) : (
        <>
          {conn === "open" && (
            <div style={{ marginBottom: "1rem" }}>
              <p
                className="a2-text a2-text--caption"
                style={{ marginBottom: "0.4rem" }}
              >
                許願地點（可拖動圖釘或點擊地圖調整）
              </p>
              <WishLocationPicker
                lat={pickerLat}
                lng={pickerLng}
                onChange={(lat, lng) => {
                  setPickerLat(lat);
                  setPickerLng(lng);
                  pickerLatRef.current = lat;
                  pickerLngRef.current = lng;
                }}
              />
            </div>
          )}
          <Renderer
            state={state}
            onEvent={onEvent}
            onDataModelChange={onDataModelChange}
            decorate={decorate}
          />
        </>
      )}

      {!offline && conn === "connecting" && state.surfaceId === null ? (
        <p className="a2-text a2-text--caption" style={{ marginTop: "1.6rem" }}>
          正在連接土地公廟…
        </p>
      ) : null}
    </WishShell>
  );
}

// ── Offline mode: replay the canned transcript (no backend) ──────────────────
function WishDemo() {
  const [state, setState] = useState<SurfaceState>(emptySurface);
  const [conn, setConn] = useState<Conn>("connecting");
  const [runId, setRunId] = useState(0);
  const timers = useRef<ReturnType<typeof setTimeout>[]>([]);

  const clearTimers = () => {
    timers.current.forEach(clearTimeout);
    timers.current = [];
  };

  useEffect(() => {
    clearTimers();
    let acc = 0;
    let live = emptySurface();

    wishDemo.forEach((msg, idx) => {
      // A reverent hush before the blessing components arrive.
      const isBlessing =
        "updateComponents" in msg &&
        msg.updateComponents.components[0]?.id === "root" &&
        msg.updateComponents.components.some((c) => c.id === "blessing-card");
      acc += idx === 0 ? 350 : isBlessing ? 1500 : 900;
      const t = setTimeout(() => {
        live = applyMessage(live, msg);
        setState(live);
        if ("a2uiDone" in msg) setConn("done");
        else setConn((c) => (c === "connecting" ? "submitted" : c));
      }, acc);
      timers.current.push(t);
    });

    return clearTimers;
  }, [runId]);

  const replay = useCallback(() => {
    clearTimers();
    setState(emptySurface());
    setConn("connecting");
    setRunId((n) => n + 1);
  }, []);

  // In the offline demo the transcript drives the surface; events are no-ops.
  const onEvent = useCallback(() => {}, []);
  const onDataModelChange = useCallback((path: string, value: unknown) => {
    setState((prev) => ({
      ...prev,
      dataModel: setAtPointer(prev.dataModel, path, value),
    }));
  }, []);

  const ready = blessingReady(state);
  const decorate = useCallback<Decorator>(
    ({ id, element }) => {
      if (id === "blessing-card" && ready) {
        return <BlessingBloom key="blessing-bloom">{element}</BlessingBloom>;
      }
      return null;
    },
    [ready],
  );

  return (
    <WishShell mode="demo" conn={conn} onReplay={replay}>
      <Renderer
        state={state}
        onEvent={onEvent}
        onDataModelChange={onDataModelChange}
        decorate={decorate}
      />
    </WishShell>
  );
}

// ── Shared chrome ────────────────────────────────────────────────────────────
function WishShell({
  mode,
  conn,
  onReplay,
  children,
}: {
  mode: "live" | "demo";
  conn: Conn;
  onReplay?: () => void;
  children: React.ReactNode;
}) {
  return (
    <IncenseBackground>
      <main className="sanctum">
        <TempleNav active="wish" />

        <div className="sanctum__brand">
          <span className="sanctum__seal">願</span>
          <span className="sanctum__kicker">
            WISH · 上香許願 {mode === "demo" ? "(offline transcript)" : "(live)"}
          </span>
        </div>

        <div className="live-status">
          <span className="live-status__dot" data-conn={conn} />
          <span className="live-status__label">{statusLabel(conn)}</span>
          {mode === "demo" ? (
            <button
              className="live-status__link"
              style={{ marginLeft: "auto", cursor: "pointer", background: "none", border: "none" }}
              onClick={onReplay}
            >
              ↻ 重新許願
            </button>
          ) : (
            <Link className="live-status__link" href="/wish?demo=1">
              觀禮展演 demo →
            </Link>
          )}
        </div>

        {children}
      </main>
    </IncenseBackground>
  );
}

// ── Route entry: pick live vs demo from ?demo=1 ──────────────────────────────
function WishRouter() {
  const params = useSearchParams();
  const demo = params.get("demo") === "1";
  return demo ? <WishDemo /> : <WishLive />;
}

export default function WishPage() {
  // useSearchParams requires a Suspense boundary in the App Router.
  return (
    <Suspense
      fallback={
        <IncenseBackground>
          <main className="sanctum">
            <p className="a2-text a2-text--caption">正在備壇…</p>
          </main>
        </IncenseBackground>
      }
    >
      <WishRouter />
    </Suspense>
  );
}
