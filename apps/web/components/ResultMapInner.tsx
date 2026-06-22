"use client";

import { useEffect, useRef } from "react";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import type { MapItineraryStop } from "./ResultMap";

// 台南中西區 — the sanctum's earthly seat.
const TAINAN_CENTER: [number, number] = [22.997, 120.201];

/**
 * Client-only Leaflet map (loaded via next/dynamic { ssr: false } from
 * ResultMap). Dark CARTO tiles, a gold divIcon per recommended POI, popups with
 * name + note. Built imperatively to fully control the divine marker styling and
 * to sidestep any SSR window access.
 */
function goldIcon() {
  return L.divIcon({
    className: "poi-divicon",
    html: `
      <span class="poi-pin">
        <span class="poi-pin__ring"></span>
        <span class="poi-pin__core">◉</span>
      </span>`,
    iconSize: [34, 34],
    iconAnchor: [17, 17],
    popupAnchor: [0, -16],
  });
}

export default function ResultMapInner({ itinerary }: { itinerary: MapItineraryStop[] }) {
  const elRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<L.Map | null>(null);

  useEffect(() => {
    if (!elRef.current || mapRef.current) return;

    const map = L.map(elRef.current, {
      center: TAINAN_CENTER,
      zoom: 15,
      scrollWheelZoom: false,
      attributionControl: true,
    });
    mapRef.current = map;

    L.tileLayer(
      "https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png",
      {
        attribution:
          '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> &copy; <a href="https://carto.com/attributions">CARTO</a>',
        subdomains: "abcd",
        maxZoom: 20,
      },
    ).addTo(map);

    const bounds: [number, number][] = [];
    const latlngs: L.LatLngExpression[] = [];
    
    for (const p of itinerary) {
      if (typeof p.lat !== "number" || typeof p.lng !== "number") continue;
      bounds.push([p.lat, p.lng]);
      latlngs.push([p.lat, p.lng]);
      const note = p.note ? `<div class="poi-popup__note">${escapeHtml(p.note)}</div>` : "";
      const cat = p.category ? `<div class="poi-popup__cat">${escapeHtml(p.category)}</div>` : "";
      L.marker([p.lat, p.lng], { icon: goldIcon() })
        .addTo(map)
        .bindPopup(
          `<div class="poi-popup">
             <div class="poi-popup__name">${escapeHtml(p.poi_name)}</div>
             ${cat}${note}
           </div>`,
          { className: "poi-popup-wrap" },
        );
    }

    if (latlngs.length > 1) {
      L.polyline(latlngs, { color: 'var(--color-primary, gold)', weight: 3, dashArray: '5, 10' }).addTo(map);
    }

    if (bounds.length === 1) {
      map.setView(bounds[0], 16);
    } else if (bounds.length > 1) {
      map.fitBounds(bounds, { padding: [48, 48], maxZoom: 16 });
    }

    // The map mounts inside an animating card; settle its size once laid out.
    const t = setTimeout(() => map.invalidateSize(), 240);

    return () => {
      clearTimeout(t);
      map.remove();
      mapRef.current = null;
    };
  }, [itinerary]);

  return <div ref={elRef} className="result-map" role="region" aria-label="土地公推薦地點輿圖" />;
}

function escapeHtml(s: string): string {
  return s
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}
