"use client";

import { useEffect, useRef } from "react";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import type {
  CouncilBoundary,
  CouncilStatementRow,
  CouncilAlignmentRow,
} from "./CouncilMap";

// 台南中西區 — the sanctum's earthly seat.
const TAINAN_CENTER: [number, number] = [22.997, 120.201];

type Stance = CouncilStatementRow["stance"];

// Boundary fill/stroke per stance. "speaking" overrides while a 里 holds the floor.
const STANCE_COLOR: Record<Stance | "base" | "speaking", string> = {
  speaking: "#f5c451", // gold
  support: "#4ade80", // green
  oppose: "#f87171", // red
  question: "#60a5fa", // blue
  inform: "#c9b894", // parchment
  silent: "#6b6256",
  base: "#6b6256", // dim, before anyone speaks
};

function baseStyle(color: string): L.PathOptions {
  return { color, weight: 1.5, fillColor: color, fillOpacity: 0.12, opacity: 0.5 };
}
function stanceStyle(color: string): L.PathOptions {
  return { color, weight: 2, fillColor: color, fillOpacity: 0.28, opacity: 0.85 };
}
function speakingStyle(): L.PathOptions {
  return {
    color: STANCE_COLOR.speaking,
    weight: 3.5,
    fillColor: STANCE_COLOR.speaking,
    fillOpacity: 0.42,
    opacity: 1,
    className: "council-boundary--speaking",
  };
}

/** Latest stance each 里 expressed, scanning the transcript in order. */
function latestStanceByAgent(statements: CouncilStatementRow[]): Map<string, Stance> {
  const m = new Map<string, Stance>();
  for (const s of statements) {
    if (s.stance !== "silent") m.set(s.agent_id, s.stance);
  }
  return m;
}

export default function CouncilMapInner({
  boundaries,
  statements,
  alignments,
}: {
  boundaries: CouncilBoundary[];
  statements: CouncilStatementRow[];
  alignments: CouncilAlignmentRow[];
}) {
  const elRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<L.Map | null>(null);
  const polysRef = useRef<Map<string, L.Polygon>>(new Map());
  const centroidRef = useRef<Map<string, [number, number]>>(new Map());
  const linesRef = useRef<L.Polyline[]>([]);

  // Create the map once on mount; destroy on unmount.
  useEffect(() => {
    if (!elRef.current) return;

    const map = L.map(elRef.current, {
      center: TAINAN_CENTER,
      zoom: 15,
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

    const t = setTimeout(() => map.invalidateSize(), 240);

    return () => {
      clearTimeout(t);
      map.remove();
      mapRef.current = null;
      polysRef.current.clear();
      centroidRef.current.clear();
      linesRef.current = [];
    };
  }, []); // mount only — never re-initialize

  // Draw boundary polygons the first time they arrive; skip on subsequent re-renders.
  useEffect(() => {
    const map = mapRef.current;
    if (!map || boundaries.length === 0 || polysRef.current.size > 0) return;

    const allBounds: [number, number][] = [];
    for (const b of boundaries) {
      if (!b.polygon || b.polygon.length === 0) continue;
      const poly = L.polygon(b.polygon, baseStyle(STANCE_COLOR.base)).addTo(map);
      poly.bindTooltip(b.street_name, { className: "council-tooltip", direction: "center" });
      polysRef.current.set(b.agent_id, poly);
      centroidRef.current.set(b.agent_id, [b.centroid.lat, b.centroid.lng]);
      for (const pt of b.polygon) allBounds.push(pt);
    }
    if (allBounds.length > 0) {
      map.fitBounds(allBounds, { padding: [40, 40], maxZoom: 16 });
    }
  }, [boundaries]);

  // React to the transcript: recolor by latest stance, highlight the speaker,
  // pan the camera, and draw a fading line to whoever they're responding to.
  useEffect(() => {
    const map = mapRef.current;
    if (!map || statements.length === 0) return;

    const latest = latestStanceByAgent(statements);
    for (const [agentId, poly] of polysRef.current) {
      const stance = latest.get(agentId);
      poly.setStyle(stance ? stanceStyle(STANCE_COLOR[stance]) : baseStyle(STANCE_COLOR.base));
    }

    const current = statements[statements.length - 1];
    const speaker = polysRef.current.get(current.agent_id);
    if (speaker) {
      speaker.setStyle(speakingStyle());
      speaker.bringToFront();
    }

    // Response line: from the addressed 里 to the speaker.
    if (current.responds_to) {
      const from = centroidRef.current.get(current.responds_to);
      const to = centroidRef.current.get(current.agent_id);
      if (from && to) {
        const color =
          current.stance === "oppose"
            ? STANCE_COLOR.oppose
            : current.stance === "support"
              ? STANCE_COLOR.support
              : STANCE_COLOR.question;
        const line = L.polyline([from, to], {
          color,
          weight: 2,
          opacity: 0.9,
          dashArray: "4 8",
        }).addTo(map);
        linesRef.current.push(line);
        // Fade older lines; keep at most 4.
        const lines = linesRef.current;
        for (let i = 0; i < lines.length - 1; i++) {
          lines[i].setStyle({ opacity: Math.max(0.15, 0.6 - (lines.length - 1 - i) * 0.18) });
        }
        while (lines.length > 4) {
          const old = lines.shift();
          if (old) old.remove();
        }
      }
    }
  }, [statements]);

  // Final consensus: recolor every 里 to its closing stance, clear transient lines.
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !alignments || alignments.length === 0) return;

    for (const line of linesRef.current) line.remove();
    linesRef.current = [];

    for (const a of alignments) {
      const poly = polysRef.current.get(a.agent_id);
      if (poly) poly.setStyle(stanceStyle(STANCE_COLOR[a.final_stance] ?? STANCE_COLOR.base));
    }
  }, [alignments]);

  return (
    <div
      ref={elRef}
      className="result-map council-map"
      role="region"
      aria-label="里長大會神界輿圖"
    />
  );
}
