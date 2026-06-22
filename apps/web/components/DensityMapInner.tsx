"use client";

import { useEffect, useRef } from "react";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import type { WishPoint } from "./DensityMap";

// 台南中西區 — the sanctum's earthly seat.
const TAINAN_CENTER: [number, number] = [22.997, 120.201];

// Category → divine tint. Anything unknown falls back to gold.
const CATEGORY_TINT: Record<string, string> = {
  社區營造: "#e8b04b", // gold
  公共安全: "#c8442e", // vermillion
  環境綠化: "#4fa88b", // jade
  交通建設: "#5b9bd5", // sky
  文化保存: "#b07ad6", // amethyst
};
const DEFAULT_TINT = "#e8b04b";

type Cell = {
  lat: number;
  lng: number;
  count: number;
  byCat: Record<string, number>;
};

// Group points into ~0.0015° cells (~150m) so clusters read as density.
function bin(points: WishPoint[]): Cell[] {
  const STEP = 0.0015;
  const cells = new Map<string, Cell>();
  for (const p of points) {
    if (typeof p.lat !== "number" || typeof p.lng !== "number") continue;
    const gy = Math.round(p.lat / STEP);
    const gx = Math.round(p.lng / STEP);
    const key = `${gy}:${gx}`;
    let cell = cells.get(key);
    if (!cell) {
      cell = { lat: gy * STEP, lng: gx * STEP, count: 0, byCat: {} };
      cells.set(key, cell);
    }
    cell.count += 1;
    cell.byCat[p.category] = (cell.byCat[p.category] ?? 0) + 1;
  }
  return [...cells.values()];
}

function dominantCategory(byCat: Record<string, number>): string {
  let best = "";
  let bestN = -1;
  for (const [cat, n] of Object.entries(byCat)) {
    if (n > bestN) {
      bestN = n;
      best = cat;
    }
  }
  return best;
}

/**
 * Client-only Leaflet density map (loaded via next/dynamic { ssr: false }).
 * Dark CARTO tiles. Wishes are binned into grid cells; each cell becomes a
 * translucent gold/category-tinted CircleMarker whose radius + opacity grow
 * with the number of wishes — a temple's reading of where the city is praying
 * hardest. No extra leaflet plugin.
 */
export default function DensityMapInner({ points }: { points: WishPoint[] }) {
  const elRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<L.Map | null>(null);

  useEffect(() => {
    if (!elRef.current || mapRef.current) return;

    const map = L.map(elRef.current, {
      center: TAINAN_CENTER,
      zoom: 14,
      scrollWheelZoom: false,
      attributionControl: true,
    });
    mapRef.current = map;

    L.tileLayer("https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png", {
      attribution:
        '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> &copy; <a href="https://carto.com/attributions">CARTO</a>',
      subdomains: "abcd",
      maxZoom: 20,
    }).addTo(map);

    const cells = bin(points);
    const maxCount = cells.reduce((m, c) => Math.max(m, c.count), 1);
    const bounds: [number, number][] = [];

    for (const cell of cells) {
      bounds.push([cell.lat, cell.lng]);
      const weight = cell.count / maxCount; // 0..1
      const tint = CATEGORY_TINT[dominantCategory(cell.byCat)] ?? DEFAULT_TINT;
      const radius = 14 + weight * 34; // px
      const fillOpacity = 0.16 + weight * 0.4;

      L.circleMarker([cell.lat, cell.lng], {
        radius,
        color: tint,
        weight: 1,
        opacity: 0.8,
        fillColor: tint,
        fillOpacity,
      })
        .addTo(map)
        .bindPopup(
          `<div class="poi-popup">
             <div class="poi-popup__name">${cell.count} 個願望</div>
             <div class="poi-popup__cat">${escapeHtml(dominantCategory(cell.byCat))}</div>
           </div>`,
          { className: "poi-popup-wrap" },
        );
    }

    if (bounds.length === 1) {
      map.setView(bounds[0], 15);
    } else if (bounds.length > 1) {
      map.fitBounds(bounds, { padding: [48, 48], maxZoom: 16 });
    }

    const t = setTimeout(() => map.invalidateSize(), 240);

    return () => {
      clearTimeout(t);
      map.remove();
      mapRef.current = null;
    };
  }, [points]);

  return (
    <div ref={elRef} className="result-map" role="region" aria-label="城市願望密度輿圖" />
  );
}

function escapeHtml(s: string): string {
  return s
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}
