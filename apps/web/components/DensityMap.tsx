"use client";

import dynamic from "next/dynamic";

export type WishPoint = { lat: number; lng: number; category: string };

/**
 * Governance density map. Leaflet touches `window` at module scope, so the real
 * map (DensityMapInner) is loaded ONLY on the client via next/dynamic
 * { ssr: false }. This wrapper is the public, prerender-safe component.
 */
const MapInner = dynamic(() => import("./DensityMapInner"), {
  ssr: false,
  loading: () => (
    <div className="result-map result-map--loading" aria-hidden>
      <span className="result-map__loading-text">展開城市風向輿圖…</span>
    </div>
  ),
});

export function DensityMap({ points }: { points: WishPoint[] }) {
  return <MapInner points={points} />;
}

export default DensityMap;
