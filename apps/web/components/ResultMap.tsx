"use client";

import dynamic from "next/dynamic";

export type MapItineraryStop = {
  day: number;
  poi_name: string;
  category?: string;
  lat: number;
  lng: number;
  tags?: string[];
  note?: string | null;
  stop_title: string;
  stop_duration: string;
  stop_activity: string;
  transit: string;
};

/**
 * Leaflet result map. Leaflet touches `window` at module scope, so the actual
 * map (MapInner) is loaded ONLY on the client via next/dynamic { ssr: false }.
 * This wrapper is the public component; the static prerender of `/` never pulls
 * Leaflet in, so the build cannot crash on a missing `window`.
 */
const MapInner = dynamic(() => import("./ResultMapInner"), {
  ssr: false,
  loading: () => (
    <div className="result-map result-map--loading" aria-hidden>
      <span className="result-map__loading-text">展開神界輿圖…</span>
    </div>
  ),
});

export function ResultMap({ itinerary }: { itinerary: MapItineraryStop[] }) {
  if (!itinerary || itinerary.length === 0) return null;
  return <MapInner itinerary={itinerary} />;
}

export default ResultMap;
