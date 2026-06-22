"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { IncenseBackground } from "@/components/theater/IncenseBackground";
import { TempleNav } from "@/components/TempleNav";
import { DensityMap, WishPoint } from "@/components/DensityMap";

const HTTP_HOST =
  process.env.NEXT_PUBLIC_GATEWAY_HTTP ?? "http://127.0.0.1:8080";

type Wish = {
  wish_id: string;
  raw_text: string;
  category: string;
  location: { lat: number; lng: number };
  photo_ref?: string | null;
  created_at: string;
  status: string;
};

type Summary = {
  total: number;
  by_category: Record<string, number>;
  points: WishPoint[];
  recent: Wish[];
};

type Source = "live" | "fallback";

// Category → tint, mirroring the density map so chips and bars read as one palette.
const CATEGORY_TINT: Record<string, string> = {
  社區營造: "var(--gold)",
  公共安全: "var(--vermillion)",
  環境綠化: "var(--jade)",
  交通建設: "#5b9bd5",
  文化保存: "#b07ad6",
};
function tint(cat: string): string {
  return CATEGORY_TINT[cat] ?? "var(--gold-glow)";
}

// Clearly-marked sample so the page renders offline for the demo (fetch failed).
const FALLBACK_SUMMARY: Summary = {
  total: 7,
  by_category: {
    社區營造: 3,
    公共安全: 2,
    環境綠化: 1,
    文化保存: 1,
  },
  points: [
    { lat: 22.9971, lng: 120.201, category: "社區營造" },
    { lat: 22.9975, lng: 120.2015, category: "社區營造" },
    { lat: 22.9968, lng: 120.2008, category: "社區營造" },
    { lat: 22.992, lng: 120.198, category: "公共安全" },
    { lat: 22.9925, lng: 120.1985, category: "公共安全" },
    { lat: 22.9938, lng: 120.1972, category: "環境綠化" },
    { lat: 22.9955, lng: 120.2025, category: "文化保存" },
  ],
  recent: [
    {
      wish_id: "demo-1",
      raw_text: "希望神農街的老房子可以被好好保存",
      category: "文化保存",
      location: { lat: 22.9955, lng: 120.2025 },
      created_at: new Date(Date.now() - 1000 * 60 * 8).toISOString(),
      status: "received",
    },
    {
      wish_id: "demo-2",
      raw_text: "海安路晚上太暗了，希望多裝幾盞路燈比較安全",
      category: "公共安全",
      location: { lat: 22.992, lng: 120.198 },
      created_at: new Date(Date.now() - 1000 * 60 * 47).toISOString(),
      status: "received",
    },
    {
      wish_id: "demo-3",
      raw_text: "希望巷口的小公園可以多種一點樹",
      category: "環境綠化",
      location: { lat: 22.9938, lng: 120.1972 },
      created_at: new Date(Date.now() - 1000 * 60 * 60 * 3).toISOString(),
      status: "received",
    },
    {
      wish_id: "demo-4",
      raw_text: "想在正興街辦個社區市集，讓街坊多認識彼此",
      category: "社區營造",
      location: { lat: 22.9971, lng: 120.201 },
      created_at: new Date(Date.now() - 1000 * 60 * 60 * 26).toISOString(),
      status: "received",
    },
  ],
};

function relativeTime(iso: string): string {
  const t = new Date(iso).getTime();
  if (Number.isNaN(t)) return "";
  const diff = Date.now() - t;
  const min = Math.round(diff / 60000);
  if (min < 1) return "剛剛";
  if (min < 60) return `${min} 分鐘前`;
  const hr = Math.round(min / 60);
  if (hr < 24) return `${hr} 小時前`;
  const day = Math.round(hr / 24);
  return `${day} 天前`;
}

export default function DashboardPage() {
  const [summary, setSummary] = useState<Summary | null>(null);
  const [source, setSource] = useState<Source>("live");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const res = await fetch(`${HTTP_HOST}/dashboard/summary`, {
          cache: "no-store",
        });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = (await res.json()) as Summary;
        if (cancelled) return;
        setSummary(data);
        setSource("live");
      } catch {
        if (cancelled) return;
        setSummary(FALLBACK_SUMMARY);
        setSource("fallback");
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const bars = useMemo(() => {
    if (!summary) return [];
    const entries = Object.entries(summary.by_category).sort(
      (a, b) => b[1] - a[1],
    );
    const max = entries.reduce((m, [, n]) => Math.max(m, n), 1);
    return entries.map(([cat, n]) => ({ cat, n, pct: Math.round((n / max) * 100) }));
  }, [summary]);

  const empty = !!summary && summary.total === 0;

  return (
    <IncenseBackground>
      <main className="sanctum sanctum--wide">
        <TempleNav active="dashboard" />

        <div className="sanctum__brand">
          <span className="sanctum__seal">卦</span>
          <span className="sanctum__kicker">DASHBOARD · 城市風向球</span>
        </div>

        {source === "fallback" && !loading ? (
          <div className="api-banner" role="status">
            <span className="api-banner__dot" />
            無法連上 gateway — 以下為展示用樣本資料（啟動 gateway 後將顯示真實願望）。
          </div>
        ) : null}

        {loading ? (
          <p className="a2-text a2-text--caption" style={{ marginTop: "2rem" }}>
            正在向土地公請示城市風向…
          </p>
        ) : empty ? (
          <div className="temple-closed" role="status">
            <div className="temple-closed__seal" style={{ color: "var(--gold)", borderColor: "rgba(232,176,75,0.6)" }}>
              願
            </div>
            <h2 className="temple-closed__title">尚無願望</h2>
            <p className="temple-closed__body">
              香爐冷清，城市還沒有人開口。快去{" "}
              <Link href="/wish" className="temple-closed__link">
                /wish 上香
              </Link>{" "}
              許下第一個願望。
            </p>
          </div>
        ) : summary ? (
          <>
            {/* ── 城市風向球：total headline + category bars ── */}
            <section className="windvane">
              <div className="windvane__headline">
                <span className="windvane__total">{summary.total}</span>
                <span className="windvane__total-label">
                  則願望
                  <br />
                  匯入香爐
                </span>
              </div>
              <div className="windvane__bars">
                {bars.map((b) => (
                  <div className="windvane-bar" key={b.cat}>
                    <div className="windvane-bar__head">
                      <span
                        className="windvane-bar__chip"
                        style={{ background: tint(b.cat) }}
                        aria-hidden
                      />
                      <span className="windvane-bar__cat">{b.cat}</span>
                      <span className="windvane-bar__n">{b.n}</span>
                    </div>
                    <div className="windvane-bar__track">
                      <div
                        className="windvane-bar__fill"
                        style={{ width: `${b.pct}%`, background: tint(b.cat) }}
                      />
                    </div>
                  </div>
                ))}
              </div>
            </section>

            {/* ── Density map ── */}
            <section className="dashboard-section">
              <h2 className="dashboard-section__title">願望密度 · 城市祈願熱區</h2>
              <p className="dashboard-section__sub">
                越亮、越大的光暈，代表該處香火越旺；色澤映其主要願望分類。
              </p>
              <DensityMap points={summary.points} />
            </section>

            {/* ── Recent wishes ── */}
            <section className="dashboard-section">
              <h2 className="dashboard-section__title">近期香火 · 最新願望</h2>
              <ul className="recent-wishes">
                {summary.recent.map((w) => (
                  <li className="recent-wish" key={w.wish_id}>
                    <span
                      className="recent-wish__chip"
                      style={{ borderColor: tint(w.category), color: tint(w.category) }}
                    >
                      {w.category}
                    </span>
                    <p className="recent-wish__text">{w.raw_text}</p>
                    <span className="recent-wish__time">{relativeTime(w.created_at)}</span>
                  </li>
                ))}
                {summary.recent.length === 0 ? (
                  <li className="recent-wish recent-wish--empty">尚無近期願望</li>
                ) : null}
              </ul>
            </section>
          </>
        ) : null}
      </main>
    </IncenseBackground>
  );
}
